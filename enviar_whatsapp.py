import time
import random
import os
from urllib.parse import quote
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
from lista_numeros import numeros_brutos, preparar_numeros

# Função para digitar simulando um ser humano
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


# Números carregados do módulo centralizado lista_numeros.py
numeros = preparar_numeros(numeros_brutos)


# =====================================================================
# SISTEMA DE MEMÓRIA DEFINITIVA (EVITAR REPETIÇÃO)
# =====================================================================
arquivo_memoria = os.path.join(os.getcwd(), "ja_enviados.txt")

# Se o arquivo não existir, cria um vazio
if not os.path.exists(arquivo_memoria):
    with open(arquivo_memoria, "w") as f:
        pass

# Lê o banco de dados local com os números que já receberam a mensagem
with open(arquivo_memoria, "r") as f:
    ja_enviados = set()
    for linha in f:
        l = linha.strip()
        # Se algum número salvo na memória antiga não tem o 55 (tamanho 10 ou 11), colocamos para bater com a lista atual
        if len(l) in (10, 11) and not l.startswith('55'):
            l = '55' + l
        ja_enviados.add(l)

# SUBTRAI da lista atual todo mundo que já foi enviado
numeros_originais_qtd = len(numeros)
numeros = [n for n in numeros if n not in ja_enviados]

print("══════════════════════════════════════════════════")
print(f"  📋 Total bruto na lista          : {numeros_originais_qtd}")
print(f"  ✅ Já enviados (memória local)    : {len(ja_enviados)}")
print(f"  🎯 Faltam enviar                  : {len(numeros)} contatos")
print("══════════════════════════════════════════════════")

if len(numeros) == 0:
    print("🎉 Todos os contatos da lista já foram processados! O robô pode descansar.")
    exit()

link_grupo = "https://chat.whatsapp.com/Js3QrauU3Y7ECPh6VWzXcN"

# =====================================================================
# EDGE-ACK: Pré-geração do lote ANTES de abrir o navegador
# Padrão n8n 2026: o worker recebe pacotes prontos, sem processar no momento crítico
# =====================================================================
lote_mensagens = pre_gerar_lote_mensagens(numeros, link_grupo)

# =====================================================================
# MISSION CONTROL: Inicializa tratamento de erros e Dead-Letter Queue
# =====================================================================
mc = MissionControl(os.getcwd())

# =====================================================================
# DASHBOARD: Inicializa painel de observabilidade em tempo real
# =====================================================================
dashboard = SessionDashboard(total_numeros=len(numeros))

print("Configurando o navegador indetectável...")
# Configurações para salvar a sessão do WhatsApp e não pedir o QR Code novamente
options = uc.ChromeOptions()
perfil_dir = os.path.join(os.getcwd(), "wpp_perfil")
options.add_argument(f"--user-data-dir={perfil_dir}")

driver = uc.Chrome(options=options, use_subprocess=True)
driver.maximize_window()

driver.get("https://web.whatsapp.com/")
print("==================================================")
print("Atenção: O navegador Chrome abriu.")
print("Se for a primeira vez, por favor, ESCANEIE O QR CODE na tela.")
print("Caso contrário, o WhatsApp conectará automaticamente na mesma conta.")
print("Aguardando carregamento da tela inicial...")
print("==================================================")

# Aguarda até 120 segundos para que o usuário escaneie o código e a tela principal carregue
try:
    # A div com id 'pane-side' é a lista lateral de conversas
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )
    print("Login no WhatsApp Web detectado com sucesso! Iniciando envios...")
    print(f"Total de números válidos e sem repetição para enviar: {len(numeros)}")
except TimeoutException:
    print("Tempo esgotado (2 minutos) aguardando você escanear o QR code. Feche e tente novamente.")
    driver.quit()
    exit()

mensagens_enviadas = 0
controle_pausas = ControlePausasOperacionais()
tempo_inicio_envio = time.time()

for i, numero in enumerate(numeros):
    # EDGE-ACK: Recupera a mensagem pré-gerada do lote (acesso O(1), sem processamento no loop)
    mensagem_completa = lote_mensagens[numero]
    
    dashboard.imprimir(
        numero_atual=numero,
        acao=f"Carregando chat [{i+1}/{len(numeros)}]..."
    )

    # Monta a URL apenas com o número. O texto será digitado humanamente.
    url = f"https://web.whatsapp.com/send?phone={numero}"
    
    driver.get(url)
    
    try:
        # PASSO 2: Aguarda a caixa de texto ficar CLICÁVEL (HCI/Robustez)
        caixa_texto = WebDriverWait(driver, 35).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]'))
        )
        
        time.sleep(1.5) # Dá um tempinho para o histórico de conversas carregar na tela
        
        # PASSO 2.5: Verificação Anti-Repetição (Verifica se já enviamos)
        try:
            # Procura por balões de mensagem que nós enviamos ("message-out")
            mensagens_nossas = driver.find_elements(By.XPATH, '//div[contains(@class, "message-out")]')
            ja_enviou = False
            
            for msg in mensagens_nossas:
                texto_msg = msg.text.lower()
                # Verifica se o ID do link do grupo ou a palavra "realess" já estão nas nossas mensagens
                if "js3qrauu3y7ecph6vwzxcn" in texto_msg or "realess" in texto_msg:
                    ja_enviou = True
                    break
                    
            if ja_enviou:
                dashboard.registrar_pulado()
                mc._log_evento("PULADO", numero, {"motivo": "Mensagem já enviada anteriormente (verificação visual)"})
                continue  # Pula para o próximo número
        except Exception:
            pass
        
        # Clica na caixa para focar (Garante interatividade)
        driver.execute_script("arguments[0].click();", caixa_texto)
        time.sleep(1)
        
        # PASSO 3: Digita a mensagem inteira simulando a velocidade de uma pessoa
        digitar_como_humano(caixa_texto, mensagem_completa, driver=driver)
        
        # Pausa para a miniatura do link carregar
        time.sleep(4)
        
        # PASSO 4: Envia usando a tecla ENTER (método humano real)
        caixa_texto.send_keys(Keys.ENTER)
        
        # PASSO 5: Validação Nível 1 - A caixa de texto esvaziou?
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]').text == ""
            )
        except TimeoutException:
            pass
            
        # PASSO 6: Validação Nível 2 - O WhatsApp confirmou o envio?
        entregue = False
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '(//span[@data-icon="msg-check" or @data-icon="msg-dblcheck"])[last()]'))
            )
            entregue = True
        except TimeoutException:
            pass  # Seguimos e registramos abaixo

        # =================================================================
        # MISSION CONTROL: Registra resultado e gerencia DLQ
        # =================================================================
        if entregue:
            print(f"  ✅ Entregue ao servidor: {numero}")
            # Memória permanente
            with open(arquivo_memoria, "a") as f:
                f.write(f"{numero}\n")
            mc.registrar_sucesso(numero)
            duracao = time.time() - tempo_inicio_envio
            dashboard.registrar_envio(duracao)
            tempo_inicio_envio = time.time()
            mensagens_enviadas += 1
        else:
            print(f"  ⚠️ Sem confirmação de check para {numero}. Registrando para retry...")
            # Ainda registra na memória para não reenviar cegamente
            with open(arquivo_memoria, "a") as f:
                f.write(f"{numero}\n")
            mc.registrar_falha(numero, motivo="Timeout no ícone de check — entrega incerta")
            dashboard.registrar_falha()
        
        # PASSO 7: Cadência + Pausas Operacionais
        pausa_longa = controle_pausas.registrar_envio_e_verificar_pausa()
        
        if pausa_longa > 0:
            dashboard.imprimir(acao=f"⏳ Pausa operacional (rate limit): {pausa_longa:.0f}s...")
            time.sleep(pausa_longa)
        else:
            espera = calcular_delay_jitter(len(mensagem_completa))
            print(f"  ⏳ Próximo envio em {espera:.1f}s (jitter gaussiano)...")
            time.sleep(espera)
            
    except TimeoutException:
        # MISSION CONTROL: Chat não carregou → falha de rede ou número inválido
        tentativas_feitas = mc.fila_retry.get(numero, 0)
        tem_retry = mc.registrar_falha(numero, motivo="Timeout ao carregar o chat — número inválido ou falha de rede")
        dashboard.registrar_falha()
        
        if tem_retry:
            delay_retry = calcular_backoff_exponencial(tentativas_feitas + 1)
            print(f"  ❌ Falha para {numero}. Backoff exponencial: aguardando {delay_retry:.0f}s antes de continuar...")
            time.sleep(delay_retry)
        else:
            print(f"  🚫 {numero} esgotou as retentativas. Adicionado à Dead-Letter Queue (falhas.txt).")

# =====================================================================
# RELATÓRIO FINAL — MISSION CONTROL + DASHBOARD
# =====================================================================
resumo = mc.resumo_final()
dashboard.imprimir_resumo_final(resumo)
driver.quit()
