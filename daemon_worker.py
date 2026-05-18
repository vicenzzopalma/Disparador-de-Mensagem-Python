import argparse
import json
import time
import os
import sys
import random
import traceback
import requests

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.keys import Keys

from motor_semantico import pre_gerar_lote_mensagens, obter_saudacao_temporal, parafrasear_ia
from cadencia import calcular_delay_jitter, ControlePausasOperacionais, calcular_backoff_exponencial
from mission_control import MissionControl
from dashboard import SessionDashboard


def escrever_memoria_com_lock(arquivo_memoria: str, numero: str):
    lock_file = arquivo_memoria + ".lock"
    while True:
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(0.05)
    try:
        with open(arquivo_memoria, "a") as f:
            f.write(f"{numero}\n")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

def digitar_como_humano(elemento, texto, driver=None):
    try:
        for letra in texto:
            elemento.send_keys(letra)
            time.sleep(random.uniform(0.01, 0.05))
    except Exception as e:
        if driver:
            driver.execute_script("arguments[0].focus();", elemento)
            elemento.send_keys(texto)

def check_status(driver):
    try:
        # Verifica banimento (Procura por textos comuns de ban)
        page_source = driver.page_source.lower()
        if "não tem permissão para usar o whatsapp" in page_source or "esta conta foi banida" in page_source or "is banned" in page_source:
            return "Banido"
            
        # Verifica se a lista de conversas carregou
        elementos = driver.find_elements(By.ID, "pane-side")
        if len(elementos) > 0:
            return "Conectado"
            
        # Verifica se está na tela de QR Code
        qr_code = driver.find_elements(By.XPATH, '//canvas[@aria-label="Scan me!"]')
        if len(qr_code) > 0 or "landing-main" in page_source:
            return "Desconectado"
            
        return "Carregando"
    except WebDriverException:
        return "ErroNavegador"


def run_campaign(driver, payload_file, conta_id, mc, diretorio_base):
    try:
        with open(payload_file, "r") as f:
            payload = json.load(f)
    except Exception as e:
        return

    numeros = payload.get("numeros", [])
    if not numeros:
        os.remove(payload_file)
        return

    link_grupo = "https://chat.whatsapp.com/Js3QrauU3Y7ECPh6VWzXcN"
    lote_mensagens = pre_gerar_lote_mensagens(numeros, link_grupo)
    
    dashboard = SessionDashboard(total_numeros=len(numeros))
    arquivo_memoria = payload.get("arquivo_memoria")
    ui_report_url = payload.get("ui_report_url")
    imagem_path = payload.get("imagem")
    custom_msg = payload.get("mensagem")

    mensagens_enviadas = 0
    controle_pausas = ControlePausasOperacionais()
    tempo_inicio_envio = time.time()
    
    diretorio_conta = os.path.join(diretorio_base, f"dados_{conta_id}")

    def check_stop_pause():
        if os.path.exists(os.path.join(diretorio_conta, "cmd_stop.json")):
            os.remove(os.path.join(diretorio_conta, "cmd_stop.json"))
            return "stop"
        while os.path.exists(os.path.join(diretorio_conta, "cmd_pause.json")):
            time.sleep(2)
        return "continue"

    def report_to_ui(action="", log=""):
        if ui_report_url:
            try:
                stats = {
                    "sent": dashboard.enviados,
                    "failed": dashboard.falhas,
                    "total": dashboard.total,
                    "eta": dashboard._calcular_eta(),
                    "action": action
                }
                requests.post(ui_report_url, json={
                    "conta_id": conta_id,
                    "stats": stats,
                    "log": log
                }, timeout=2)
            except:
                pass

    for i, numero in enumerate(numeros):
        status = check_stop_pause()
        if status == "stop":
            break
            
        mensagem_completa = lote_mensagens[numero]
        dashboard.imprimir(numero_atual=numero, acao=f"[{conta_id}] Carregando chat [{i+1}/{len(numeros)}]...")
        report_to_ui(action=f"Carregando chat {i+1}/{len(numeros)}", log=f"Processando {numero}")

        url = f"https://web.whatsapp.com/send?phone={numero}"
        driver.get(url)

        try:
            caixa_texto = WebDriverWait(driver, 35).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]'))
            )
            time.sleep(1.5)

            # Anti-Repetição Visual
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

            if imagem_path and os.path.exists(imagem_path):
                try:
                    btn_attach = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//div[@title="Anexar"] | //span[@data-icon="plus"]'))
                    )
                    btn_attach.click()
                    time.sleep(1)
                    file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
                    file_input.send_keys(imagem_path)
                    btn_send_img = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
                    )
                    time.sleep(1)
                    btn_send_img.click()
                    time.sleep(2)
                except Exception as e:
                    print(f"  [{conta_id}] Falha imagem: {e}")

            texto_enviar = custom_msg if custom_msg else mensagem_completa

            if texto_enviar:
                if "{{saudacao_temporal}}" in texto_enviar:
                    texto_enviar = texto_enviar.replace("{{saudacao_temporal}}", obter_saudacao_temporal())
                import re
                def replace_spintax(match):
                    options = match.group(1).split('|')
                    return random.choice(options)
                while '{' in texto_enviar and '|' in texto_enviar and '}' in texto_enviar:
                    texto_enviar = re.sub(r'\{([^{}]*)\}', replace_spintax, texto_enviar)
                texto_enviar = parafrasear_ia(texto_enviar)

            digitar_como_humano(caixa_texto, texto_enviar, driver=driver)
            time.sleep(4)
            caixa_texto.send_keys(Keys.ENTER)

            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.find_element(By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]').text == ""
                )
            except TimeoutException:
                pass

            entregue = False
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '(//span[@data-icon="msg-check" or @data-icon="msg-dblcheck"])[last()]'))
                )
                entregue = True
            except TimeoutException:
                pass

            if entregue:
                escrever_memoria_com_lock(arquivo_memoria, numero)
                mc.registrar_sucesso(numero)
                duracao = time.time() - tempo_inicio_envio
                dashboard.registrar_envio(duracao)
                tempo_inicio_envio = time.time()
                mensagens_enviadas += 1
                report_to_ui(action="Envio concluído", log=f"✅ Sucesso: {numero}")
            else:
                escrever_memoria_com_lock(arquivo_memoria, numero)
                mc.registrar_falha(numero, motivo="Timeout no check — entrega incerta")
                dashboard.registrar_falha()
                report_to_ui(action="Falha técnica", log=f"⚠️ Entrega incerta: {numero}")

            pausa_longa = controle_pausas.registrar_envio_e_verificar_pausa()
            if pausa_longa > 0:
                dashboard.imprimir(acao=f"[{conta_id}] ⏳ Pausa operacional: {pausa_longa:.0f}s...")
                report_to_ui(action=f"Pausa operacional {pausa_longa:.0f}s")
                time.sleep(pausa_longa)
            else:
                espera = calcular_delay_jitter(len(mensagem_completa))
                report_to_ui(action=f"Aguardando {espera:.1f}s")
                time.sleep(espera)

        except TimeoutException:
            tentativas_feitas = mc.fila_retry.get(numero, 0)
            tem_retry = mc.registrar_falha(numero, motivo="Timeout ao carregar o chat")
            dashboard.registrar_falha()
            report_to_ui(action="Erro de conexão", log=f"❌ Falha: {numero}")
            if tem_retry:
                delay_retry = calcular_backoff_exponencial(tentativas_feitas + 1)
                time.sleep(delay_retry)
            
    # Relatório final
    resumo = mc.resumo_final()
    dashboard.imprimir_resumo_final(resumo)
    report_to_ui(action="Concluido", log="Sessão finalizada")
    os.remove(payload_file)
    # Retorna para a raiz (limpa o chat atual da tela)
    driver.get("https://web.whatsapp.com/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conta-id", required=True)
    parser.add_argument("--perfil", required=True)
    parser.add_argument("--status-url", required=True)
    args = parser.parse_args()

    conta_id = args.conta_id
    diretorio_base = os.getcwd()
    diretorio_conta = os.path.join(diretorio_base, f"dados_{conta_id}")
    os.makedirs(diretorio_conta, exist_ok=True)
    
    mc = MissionControl(diretorio_conta)

    options = uc.ChromeOptions()
    perfil_dir = os.path.join(diretorio_base, args.perfil)
    options.add_argument(f"--user-data-dir={perfil_dir}")

    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.minimize_window()  # Inicia oculto/minimizado
    driver.get("https://web.whatsapp.com/")
    
    print(f"[{conta_id}] Daemon iniciado. Monitorando conexao...")

    while True:
        try:
            # 1. Verifica Comandos no Diretório
            cmd_show = os.path.join(diretorio_conta, "cmd_show.json")
            cmd_hide = os.path.join(diretorio_conta, "cmd_hide.json")
            cmd_quit = os.path.join(diretorio_conta, "cmd_quit.json")
            cmd_send = os.path.join(diretorio_conta, "cmd_send.json")

            if os.path.exists(cmd_show):
                driver.maximize_window()
                os.remove(cmd_show)
            
            if os.path.exists(cmd_hide):
                driver.minimize_window()
                os.remove(cmd_hide)

            if os.path.exists(cmd_quit):
                os.remove(cmd_quit)
                driver.quit()
                break

            if os.path.exists(cmd_send):
                run_campaign(driver, cmd_send, conta_id, mc, diretorio_base)

            # 2. Verifica Status e Informa Servidor
            current_status = check_status(driver)
            try:
                requests.post(args.status_url, json={
                    "conta_id": conta_id,
                    "status": current_status
                }, timeout=2)
            except:
                pass

            time.sleep(3)

        except Exception as e:
            with open(os.path.join(diretorio_conta, "crash_daemon.txt"), "a") as f:
                f.write(f"\nCRITICAL DAEMON ERROR: {traceback.format_exc()}\n")
            time.sleep(5)

if __name__ == "__main__":
    main()
