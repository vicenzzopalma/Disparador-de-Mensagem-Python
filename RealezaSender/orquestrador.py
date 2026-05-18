"""
orquestrador.py
===============
Coordenador Multi-Conta para disparo paralelo via WhatsApp Web.
Baseado no padrão "Orchestrator-Worker" (n8n 2026).

Como usar:
  1. Configure a lista de contas abaixo (CONTAS).
  2. Execute: python orquestrador.py
  3. Cada conta abrirá sua própria janela do Chrome.
  4. Se for a 1ª vez de uma conta, escaneie o QR code na janela correspondente.

A lista total de números é dividida igualmente entre as contas ativas.
Números já enviados (ja_enviados.txt) são excluídos antes da divisão.
"""

import os
import sys
import json
import subprocess
import math
import time
import socket

from lista_numeros import numeros_brutos, preparar_numeros


# ═══════════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÃO DAS CONTAS — EDITE AQUI
# ═══════════════════════════════════════════════════════════════
# Adicione ou remova dicionários para cada conta WhatsApp.
# "id"     : identificador único (usado nos nomes de pasta e logs)
# "perfil" : nome da pasta onde a sessão do Chrome será salva
#            (cada conta DEVE ter uma pasta diferente)
CONTAS = [
    {"id": "CONTA_01", "perfil": "wpp_perfil_01"},
    {"id": "CONTA_02", "perfil": "wpp_perfil_02"},
]

# Link do grupo WhatsApp (o mesmo para todos os workers)
LINK_GRUPO = "https://chat.whatsapp.com/Js3QrauU3Y7ECPh6VWzXcN"

# Arquivo de memória compartilhado entre todas as contas
ARQUIVO_MEMORIA = os.path.join(os.getcwd(), "ja_enviados.txt")
# ═══════════════════════════════════════════════════════════════


def dividir_lista(lista: list, n_partes: int) -> list[list]:
    """
    Divide a lista em N partes aproximadamente iguais (sem sobreposição).
    Garante que nenhum número seja enviado por duas contas ao mesmo tempo.
    """
    tamanho = math.ceil(len(lista) / n_partes)
    return [lista[i:i + tamanho] for i in range(0, len(lista), tamanho)]


def carregar_ja_enviados() -> set:
    """Lê a memória de números já processados."""
    ja_enviados = set()
    if not os.path.exists(ARQUIVO_MEMORIA):
        with open(ARQUIVO_MEMORIA, "w") as f:
            pass
        return ja_enviados

    with open(ARQUIVO_MEMORIA, "r") as f:
        for linha in f:
            l = linha.strip()
            if l:
                if len(l) in (10, 11) and not l.startswith('55'):
                    l = '55' + l
                ja_enviados.add(l)
    return ja_enviados


def carregar_falhas_acumuladas() -> list:
    """
    Busca em todas as pastas de dados das contas por números que caíram na Dead-Letter Queue.
    Padrão n8n 2026: Reprocessamento de DLQ.
    """
    falhas_gerais = []
    diretorio_atual = os.getcwd()
    for item in os.listdir(diretorio_atual):
        if item.startswith("dados_") and os.path.isdir(item):
            caminho_falhas = os.path.join(item, "falhas.txt")
            if os.path.exists(caminho_falhas):
                with open(caminho_falhas, "r") as f:
                    falhas_gerais.extend([l.strip() for l in f if l.strip()])
    return list(set(falhas_gerais))  # Deduplica


def verificar_internet(host="8.8.8.8", port=53, timeout=3):
    """
    Verifica latência e conectividade antes de iniciar.
    Padrão n8n 2026: Health Check antecipado.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def main():
    print("═" * 60)
    print("  🎯  ORQUESTRADOR MULTI-CONTA — INICIANDO")
    print("═" * 60)
    print(f"  Contas configuradas : {len(CONTAS)}")
    for c in CONTAS:
        print(f"    • [{c['id']}] → perfil: {c['perfil']}/")
    print("═" * 60)

    # ── Prepara e filtra a lista de números ──
    todos_numeros = preparar_numeros(numeros_brutos)
    ja_enviados = carregar_ja_enviados()
    falhas_dlq = carregar_falhas_acumuladas()

    # Prioridade: Números da lista bruta que não foram enviados
    numeros_restantes = [n for n in todos_numeros if n not in ja_enviados]
    
    # Adiciona falhas de sessões anteriores que podem ser tentadas novamente
    for f in falhas_dlq:
        if f not in ja_enviados and f not in numeros_restantes:
            numeros_restantes.append(f)

    print(f"\n  🌐 Verificando conexão...")
    if not verificar_internet():
        print("  ❌ Sem conexão com a internet. Verifique seu Wi-Fi/Cabo e tente novamente.")
        sys.exit(1)
    print("  ✅ Conectividade estável detectada.")

    print(f"\n  📋 Total bruto             : {len(todos_numeros)}")
    print(f"  ⚠️  Falhas para reprocessar : {len(falhas_dlq)}")
    print(f"  ✅ Já enviados (memória)   : {len(ja_enviados)}")
    print(f"  🎯 Restantes para envio    : {len(numeros_restantes)}")

    if not numeros_restantes:
        print("\n  🎉 Todos os contatos já foram processados!")
        sys.exit(0)

    # ── Divide a lista entre as contas ──
    partes = dividir_lista(numeros_restantes, len(CONTAS))

    # Garante que o número de partes não ultrapasse o número de contas
    while len(partes) < len(CONTAS):
        partes.append([])

    print(f"\n  📦 Distribuição por conta:")
    for i, conta in enumerate(CONTAS):
        qtd = len(partes[i]) if i < len(partes) else 0
        print(f"    • [{conta['id']}] → {qtd} números")
    print()

    # ── Grava os arquivos JSON temporários por conta ──
    arquivos_temp = []
    for i, conta in enumerate(CONTAS):
        numeros_conta = partes[i] if i < len(partes) else []
        caminho_json = os.path.join(os.getcwd(), f"_temp_numeros_{conta['id']}.json")
        with open(caminho_json, "w") as f:
            json.dump(numeros_conta, f)
        arquivos_temp.append(caminho_json)

    # ── Lança os workers como subprocessos independentes ──
    processos = []
    print("  🚀 Lançando workers...\n")

    for i, conta in enumerate(CONTAS):
        if not partes[i]:
            print(f"  ⚠️  [{conta['id']}] Sem números para processar. Pulando.")
            continue

        cmd = [
            sys.executable, "worker.py",
            "--conta-id",        conta["id"],
            "--perfil",          conta["perfil"],
            "--numeros-json",    arquivos_temp[i],
            "--arquivo-memoria", ARQUIVO_MEMORIA,
        ]

        # Cada worker abre em uma nova janela de terminal (CREATE_NEW_CONSOLE no Windows)
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            processos.append((conta["id"], proc))
            print(f"  ✅ [{conta['id']}] Worker iniciado (PID: {proc.pid})")
            # Pequeno delay para não abrir todas as janelas do Chrome ao mesmo tempo
            time.sleep(3)
        except Exception as e:
            print(f"  ❌ [{conta['id']}] Falha ao iniciar worker: {e}")

    if not processos:
        print("\n  ❌ Nenhum worker foi iniciado. Verifique a configuração.")
        sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  ⏳ {len(processos)} worker(s) rodando em paralelo.")
    print(f"     Cada um tem sua própria janela de terminal e Chrome.")
    print(f"     Este terminal monitorará o estado dos processos.")
    print(f"{'═'*60}\n")

    # ── Aguarda todos os workers terminarem ──
    while True:
        todos_terminaram = True
        status_linha = []
        for conta_id, proc in processos:
            ret = proc.poll()
            if ret is None:
                todos_terminaram = False
                status_linha.append(f"[{conta_id}: RODANDO]")
            elif ret == 0:
                status_linha.append(f"[{conta_id}: ✅ CONCLUÍDO]")
            else:
                status_linha.append(f"[{conta_id}: ❌ ERRO cod={ret}]")

        print(f"\r  Status → {' | '.join(status_linha)}", end="", flush=True)

        if todos_terminaram:
            break
        time.sleep(10)

    print(f"\n\n{'═'*60}")
    print(f"  🏁  TODOS OS WORKERS FINALIZADOS")
    print(f"{'═'*60}")

    # ── Limpeza dos arquivos temporários ──
    for caminho in arquivos_temp:
        try:
            os.remove(caminho)
        except Exception:
            pass

    print(f"  📋 Logs por conta disponíveis em: dados_<conta_id>/")
    print(f"  📋 Memória geral: {ARQUIVO_MEMORIA}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
