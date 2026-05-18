"""
motor_semantico.py
==================
Padrão: "Motor de Variação Semântica" + "Edge-ACK" (n8n 2026 / HCI)
- Saudações contextuais por período do dia (Manhã/Tarde/Noite)
- Variação Semântica Dinâmica via estrutura de dicionários cruzados
- Pré-geração de lote (Edge-ACK): todas as mensagens são montadas ANTES do navegador abrir,
  eliminando a latência de processamento no momento crítico do envio.
"""
import datetime
import random

def obter_saudacao_temporal():
    """Retorna uma saudação baseada na hora atual do sistema."""
    agora = datetime.datetime.now()
    hora = agora.hour

    if 5 <= hora < 12:
        periodo = "manha"
    elif 12 <= hora < 18:
        periodo = "tarde"
    else:
        periodo = "noite"

    saudacoes = {
        "manha": [
            "Bom dia!", "Olá, bom dia!", "Bom dia, tudo bem?",
            "Passando para te desejar um bom dia!", "Opa, bom dia!",
            "Bom dia! Espero que esteja bem.", "Bom dia equipe!"
        ],
        "tarde": [
            "Boa tarde!", "Olá, boa tarde!", "Boa tarde, tudo bem?",
            "Passando para te desejar uma ótima tarde!", "Opa, boa tarde!",
            "Boa tarde! Espero que esteja bem."
        ],
        "noite": [
            "Boa noite!", "Olá, boa noite!", "Boa noite, tudo bem?",
            "Passando para deixar uma boa noite!", "Opa, boa noite!",
            "Boa noite! Espero que esteja bem."
        ]
    }

    return random.choice(saudacoes[periodo])

def gerar_variacao_mensagem():
    """
    Gera uma mensagem dinamicamente usando uma estrutura de dicionários 
    para garantir alta variação semântica e evitar padrões fixos.
    """
    
    # 1. Abertura contextual
    aberturas = [
        "Somos da Realess, cuidamos da cobrança da Seara.",
        "Aqui é da equipe Realess, responsáveis pela cobrança da Seara.",
        "A Realess (cobrança oficial da Seara) está entrando em contato.",
        "Nós representamos a Realess na parte de cobrança da Seara.",
        "Gostaríamos de informar que a Realess (parceira de cobrança da Seara) está com novidades.",
        "Somos a Realess e fazemos a gestão de cobrança da Seara."
    ]

    # 2. Motivo
    motivos = [
        "A pedido do setor administrativo, estamos criando este grupo",
        "Estamos montando este grupo por solicitação da administração",
        "Por orientação do nosso administrativo, abrimos este canal",
        "Recebemos o direcionamento da gestão administrativa para criar este grupo",
        "O setor administrativo pediu para estruturarmos este espaço"
    ]

    # 3. Objetivo Final
    objetivos = [
        "para facilitar a comunicação entre cobrança, área comercial e os clientes da SEARA.",
        "com o objetivo de melhorar e agilizar as tratativas entre cobrança, comercial e vocês, clientes.",
        "visando aprimorar o contato diário entre clientes, departamento comercial e nosso time de cobrança.",
        "para conectar de forma direta o time comercial, os clientes e a nossa central.",
        "a fim de alinhar e simplificar o contato entre os vendedores, clientes e a cobrança."
    ]

    # 4. Benefício / Chamada (Call to Action/Vantagem)
    beneficios = [
        "Dessa forma, teremos mais agilidade no acesso aos boletos em atraso e na resolução de pendências.",
        "Isso vai nos ajudar a ter um acesso mais rápido a faturas e facilitar o atendimento em geral.",
        "Assim garantimos mais velocidade no suporte, reemissão de boletos e no atendimento.",
        "Com esse canal, facilitamos o envio de 2ª via e prestamos um suporte mais dinâmico.",
        "A ideia é resolver pendências mais rápido e enviar boletos atrasados com facilidade.",
        "Acreditamos que assim qualquer necessidade financeira será resolvida de imediato."
    ]

    abertura_escolhida = random.choice(aberturas)
    motivo_escolhido = random.choice(motivos)
    objetivo_escolhido = random.choice(objetivos)
    beneficio_escolhido = random.choice(beneficios)

    # Monta o texto final garantindo espaçamento correto
    texto_final = f"{abertura_escolhida} {motivo_escolhido} {objetivo_escolhido}\n\n{beneficio_escolhido}"
    
    return texto_final


def parafrasear_ia(texto: str) -> str:
    """
    Simula uma IA reescrevendo a mensagem.
    Busca palavras-chave e as substitui por sinônimos aleatórios.
    """
    import re
    
    # Mapa de sinônimos para termos comuns de atendimento/cobrança
    sinonimos = {
        r"\bentrar em contato\b": ["chamar você", "te mandar uma mensagem", "falar com você", "estabelecer contato"],
        r"\bvou\b": ["irei", "pretendo", "estou prestes a"],
        r"\bpreciso\b": ["necessito", "gostaria", "precisava"],
        r"\benviar\b": ["mandar", "encaminhar", "disponibilizar"],
        r"\bboletos\b": ["faturas", "títulos", "documentos de cobrança", "boletos bancários"],
        r"\bagilizar\b": ["acelerar", "facilitar", "tornar mais rápido", "otimizar"],
        r"\bresolver\b": ["solucionar", "tratar", "dar andamento em"],
        r"\bpendências\b": ["atrasos", "débitos", "questões abertas"],
        r"\btudo bem\b": ["como vai?", "tudo certo?", "tudo ótimo?"],
        r"\bagradeço\b": ["obrigado", "grato", "desde já agradeço"],
        r"\batenciosamente\b": ["abs", "abraços", "até logo", "cordialmente"]
    }
    
    texto_novo = texto
    for padrao, opcoes in sinonimos.items():
        # Decide se vai trocar ou não (40% de chance para manter naturalidade)
        if random.random() > 0.6:
            texto_novo = re.sub(padrao, random.choice(opcoes), texto_novo, flags=re.IGNORECASE)
            
    return texto_novo

def pre_gerar_lote_mensagens(numeros: list, link_grupo: str) -> dict:
    """
    Padrão Edge-ACK: pré-computa o lote completo de mensagens ANTES de abrir o navegador.
    """
    print("[Edge-ACK] Pre-gerando lote de mensagens antes de abrir o navegador...")
    lote = {}
    for numero in numeros:
        saudacao = obter_saudacao_temporal()
        corpo = gerar_variacao_mensagem()
        # Aplica a "IA" de parafraseamento
        corpo_ia = parafrasear_ia(corpo)
        lote[numero] = f"{saudacao}\n\n{corpo_ia}\n\n{link_grupo}"
    
    print(f"[Edge-ACK] {len(lote)} mensagens pre-geradas e prontas para disparo.\n")
    return lote
