"""
worker.py
=========
Worker autônomo de envio para uma única conta WhatsApp.
Executado como subprocesso independente pelo orquestrador.py.

Uso:
    python worker.py --conta-id conta_1 --perfil wpp_perfil_conta1 --numeros-json numeros_conta1.json

Cada worker tem:
  - Seu próprio perfil Chrome (sessão de conta separada)
  - Seu próprio Mission Control (logs e Dead-Letter Queue isolados por pasta)
  - Seu próprio Dashboard de terminal
  - Escrita segura (lock de arquivo) no ja_enviados.txt compartilhado
"""

import argparse
import json
import time
import os
import sys
import random

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

from motor_semantico import pre_gerar_lote_mensagens
from cadencia import calcular_delay_jitter, ControlePausasOperacionais, calcular_backoff_exponencial
from mission_control import MissionControl
from dashboard import SessionDashboard


# ─────────────────────────────────────────────
# Escrita segura com lock de arquivo (Windows)
# ─────────────────────────────────────────────
def escrever_memoria_com_lock(arquivo_memoria: str, numero: str):
    """
    Escreve no arquivo compartilhado ja_enviados.txt de forma segura,
    usando um arquivo .lock para evitar corrupção quando múltiplos
    workers escrevem simultaneamente.
    """
    lock_file = arquivo_memoria + ".lock"
    while True:
        try:
            # Tenta criar o lock (operação atômica no SO)
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(0.05)  # Outro worker está escrevendo, aguarda
    try:
        with open(arquivo_memoria, "a") as f:
            f.write(f"{numero}\n")
    finally:
        os.remove(lock_file)  # Libera o lock sempre, mesmo em caso de erro


def digitar_como_humano(elemento, texto, driver=None):
    """Simula a cadência de digitação humana com garantia de foco."""
    import random
    try:
        for letra in texto:
            elemento.send_keys(letra)
            time.sleep(random.uniform(0.01, 0.05))
    except Exception as e:
        # Se falhar no meio, tenta focar de novo via JS e continuar
        if driver:
            driver.execute_script("arguments[0].focus();", elemento)
            elemento.send_keys(texto) # Se falhou o 'humano', manda o resto de uma vez para não perder o envio


# ─────────────────────────────────────────────
# Entrypoint principal do Worker
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Worker de envio WhatsApp para uma conta.")
    parser.add_argument("--conta-id", required=True, help="Identificador da conta (ex: conta_1)")
    parser.add_argument("--perfil", required=True, help="Nome da pasta do perfil Chrome (ex: wpp_perfil_conta1)")
    parser.add_argument("--numeros-json", required=True, help="Caminho para o arquivo JSON com a lista de números desta conta")
    parser.add_argument("--arquivo-memoria", required=True, help="Caminho para o ja_enviados.txt compartilhado")
    parser.add_argument("--ui-report-url", help="URL opcional para reportar progresso à UI Web")
    parser.add_argument("--login-only", action="store_true", help="Apenas abre o navegador para login e encerra após detecção")
    parser.add_argument("--imagem", help="Caminho para imagem a ser enviada")
    parser.add_argument("--mensagem", help="Mensagem customizada que sobrescreve o motor semântico")
    args = parser.parse_args()

    conta_id = args.conta_id
    diretorio_base = os.getcwd()

    # ── Carrega a lista de números atribuída a este worker ──
    with open(args.numeros_json, "r") as f:
        numeros = json.load(f)

    if not numeros and not args.login_only:
        print(f"[{conta_id}] Nenhum número para processar. Encerrando.")
        sys.exit(0)

    link_grupo = "https://chat.whatsapp.com/Js3QrauU3Y7ECPh6VWzXcN"

    # ── EDGE-ACK: Pré-geração do lote antes de abrir o navegador ──
    lote_mensagens = pre_gerar_lote_mensagens(numeros, link_grupo)

    # ── Mission Control isolado por conta ──
    diretorio_conta = os.path.join(diretorio_base, f"dados_{conta_id}")
    os.makedirs(diretorio_conta, exist_ok=True)
    mc = MissionControl(diretorio_conta)

    # ── Dashboard isolado por conta ──
    dashboard = SessionDashboard(total_numeros=len(numeros))

    # ── Configura o Chrome com o perfil desta conta ──
    print(f"\n{'='*55}")
    print(f"  WORKER [{conta_id.upper()}] - {len(numeros)} numeros atribuidos")
    print(f"{'='*55}")
    print(f"  Perfil Chrome : {args.perfil}")
    print(f"  Logs e DLQ    : dados_{conta_id}/")
    print(f"{'='*55}\n")

    options = uc.ChromeOptions()
    perfil_dir = os.path.join(diretorio_base, args.perfil)
    options.add_argument(f"--user-data-dir={perfil_dir}")

    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.maximize_window()

    driver.get("https://web.whatsapp.com/")
    print(f"[{conta_id}] Aguardando login no WhatsApp Web (escaneie o QR code se necessário)...")

    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        print(f"[{conta_id}] Login detectado!")
        
        if args.login_only:
            print(f"[{conta_id}] Modo Login Detectado. Encerrando em 5 segundos...")
            time.sleep(5)
            driver.quit()
            sys.exit(0)
            
        print(f"[{conta_id}] Iniciando envios...\n")
    except TimeoutException:
        print(f"[{conta_id}] ❌ Timeout ao aguardar QR code. Encerrando este worker.")
        driver.quit()
        sys.exit(1)

    mensagens_enviadas = 0
    controle_pausas = ControlePausasOperacionais()
    tempo_inicio_envio = time.time()

    def report_to_ui(action="", log=""):
        if args.ui_report_url:
            import requests
            try:
                stats = {
                    "sent": dashboard.enviados,
                    "failed": dashboard.falhas,
                    "total": dashboard.total,
                    "eta": dashboard._calcular_eta(),
                    "action": action
                }
                resp = requests.post(args.ui_report_url, json={
                    "conta_id": conta_id,
                    "stats": stats,
                    "log": log
                }, timeout=2)
                
                # Se a UI reportar que está pausado, entra em loop de espera
                if resp.status_code == 200:
                    status_atual = resp.json().get("status")
                    while status_atual == "paused":
                        time.sleep(3)
                        # Re-checa o status continuamente
                        r = requests.get(args.ui_report_url.replace("report_progress", "status"), timeout=2)
                        status_atual = r.json().get("status")
            except:
                pass

    try:
        for i, numero in enumerate(numeros):
            mensagem_completa = lote_mensagens[numero]

            dashboard.imprimir(
                numero_atual=numero,
                acao=f"[{conta_id}] Carregando chat [{i+1}/{len(numeros)}]..."
            )
            report_to_ui(action=f"Carregando chat {i+1}/{len(numeros)}", log=f"Processando {numero}")

            url = f"https://web.whatsapp.com/send?phone={numero}"
            driver.get(url)

            try:
                caixa_texto = WebDriverWait(driver, 35).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]'))
                )

                time.sleep(1.5)

                # ── Verificação Anti-Repetição ──
                try:
                    mensagens_nossas = driver.find_elements(By.XPATH, '//div[contains(@class, "message-out")]')
                    ja_enviou = False
                    for msg in mensagens_nossas:
                        texto_msg = msg.text.lower()
                        if "js3qrauu3y7ecph6vwzxcn" in texto_msg or "realess" in texto_msg:
                            ja_enviou = True
                            break
                    if ja_enviou:
                        dashboard.registrar_pulado()
                        mc._log_evento("PULADO", numero, {"motivo": "Mensagem já enviada (verificação visual)", "conta": conta_id})
                        report_to_ui(action="Pulado (já enviado)", log=f"Pulado {numero} (já enviado)")
                        continue
                except Exception:
                    pass

                # Se houver imagem, envia primeiro
                if args.imagem and os.path.exists(args.imagem):
                    try:
                        # Clica no botão de anexo (+)
                        btn_attach = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, '//div[@title="Anexar"] | //span[@data-icon="plus"]'))
                        )
                        btn_attach.click()
                        time.sleep(1)
                        
                        # Seleciona o input de arquivo (geralmente o primeiro input type=file)
                        file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
                        file_input.send_keys(args.imagem)
                        
                        # Aguarda o botão de enviar imagem aparecer
                        btn_send_img = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
                        )
                        time.sleep(1)
                        btn_send_img.click()
                        time.sleep(2) # Aguarda o upload concluir
                    except Exception as e:
                        print(f"  [{conta_id}] ⚠️ Falha ao enviar imagem: {e}")

                # Usa a mensagem customizada ou a do lote
                texto_enviar = args.mensagem if args.mensagem else mensagem_completa

                # ── Processamento de Aleatoriedade (SpinTax e Placeholders) ──
                if texto_enviar:
                    # 1. Placeholder de Saudação Temporal
                    if "{{saudacao_temporal}}" in texto_enviar:
                        from motor_semantico import obter_saudacao_temporal
                        texto_enviar = texto_enviar.replace("{{saudacao_temporal}}", obter_saudacao_temporal())

                    # 2. SpinTax: {opcao1|opcao2|opcao3}
                    import re
                    def replace_spintax(match):
                        options = match.group(1).split('|')
                        return random.choice(options)
                    
                    while '{' in texto_enviar and '|' in texto_enviar and '}' in texto_enviar:
                        texto_enviar = re.sub(r'\{([^{}]*)\}', replace_spintax, texto_enviar)

                    # 3. Motor de Parafraseamento IA (Sinônimos Semânticos)
                    from motor_semantico import parafrasear_ia
                    texto_enviar = parafrasear_ia(texto_enviar)

                digitar_como_humano(caixa_texto, texto_enviar, driver=driver)
                time.sleep(4)

                caixa_texto.send_keys(Keys.ENTER)

                # ── Validação Nível 1: Caixa esvaziou? ──
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]').text == ""
                    )
                except TimeoutException:
                    pass

                # ── Validação Nível 2: Check de entrega ──
                entregue = False
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, '(//span[@data-icon="msg-check" or @data-icon="msg-dblcheck"])[last()]'))
                    )
                    entregue = True
                except TimeoutException:
                    pass

                # ── Mission Control: Registra resultado ──
                if entregue:
                    print(f"  [{conta_id}] Sucesso: {numero}")
                    escrever_memoria_com_lock(args.arquivo_memoria, numero)
                    mc.registrar_sucesso(numero)
                    duracao = time.time() - tempo_inicio_envio
                    dashboard.registrar_envio(duracao)
                    tempo_inicio_envio = time.time()
                    mensagens_enviadas += 1
                    report_to_ui(action="Envio concluído", log=f"✅ Sucesso: {numero}")
                else:
                    print(f"  [{conta_id}] ⚠️ Sem check para {numero}. Registrando...")
                    escrever_memoria_com_lock(args.arquivo_memoria, numero)
                    mc.registrar_falha(numero, motivo="Timeout no check — entrega incerta")
                    dashboard.registrar_falha()
                    report_to_ui(action="Falha técnica", log=f"⚠️ Entrega incerta: {numero}")

                # ── Cadência: Jitter ou Cool-down ──
                pausa_longa = controle_pausas.registrar_envio_e_verificar_pausa()
                if pausa_longa > 0:
                    dashboard.imprimir(acao=f"[{conta_id}] ⏳ Pausa operacional: {pausa_longa:.0f}s...")
                    report_to_ui(action=f"Pausa operacional {pausa_longa:.0f}s")
                    time.sleep(pausa_longa)
                else:
                    espera = calcular_delay_jitter(len(mensagem_completa))
                    print(f"  [{conta_id}] ⏳ Próximo em {espera:.1f}s...")
                    report_to_ui(action=f"Aguardando {espera:.1f}s")
                    time.sleep(espera)

            except TimeoutException:
                tentativas_feitas = mc.fila_retry.get(numero, 0)
                tem_retry = mc.registrar_falha(numero, motivo="Timeout ao carregar o chat")
                dashboard.registrar_falha()
                report_to_ui(action="Erro de conexão", log=f"❌ Falha: {numero}")
                if tem_retry:
                    delay_retry = calcular_backoff_exponencial(tentativas_feitas + 1)
                    print(f"  [{conta_id}] ❌ Falha para {numero}. Backoff: {delay_retry:.0f}s...")
                    time.sleep(delay_retry)
                else:
                    print(f"  [{conta_id}] 🚫 {numero} esgotou retentativas → DLQ (dados_{conta_id}/falhas.txt)")
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL ERROR in Worker {conta_id}:\n{traceback.format_exc()}"
        print(f"\n{error_msg}")
        with open(os.path.join(diretorio_conta, "crash_log.txt"), "a") as f:
            f.write(f"\n{'='*40}\n{time.ctime()}\n{error_msg}\n")
        report_to_ui(action="Erro Crítico", log="Worker caiu (ver crash_log.txt)")
        time.sleep(10) # Permite ver o erro antes da janela fechar

    # ── Relatório final deste worker ──
    resumo = mc.resumo_final()
    dashboard.imprimir_resumo_final(resumo)
    report_to_ui(action="Concluido", log="Sessao finalizada")
    print(f"\n[{conta_id}] Worker encerrado. {mensagens_enviadas} mensagens entregues.\n")
    driver.quit()


if __name__ == "__main__":
    main()
