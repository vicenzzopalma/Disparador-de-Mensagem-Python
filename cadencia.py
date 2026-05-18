"""
cadencia.py
===========
Padrão: "Análise Comportamental Heurística" + "Tolerância a Falhas" (n8n 2026)
- Jitter Gaussiano não-linear baseado no tamanho da mensagem (simula leitura humana)
- Pausas Operacionais orgânicas por volume (cool-down periods)
- Backoff Exponencial para retentativas: evita hammering em APIs com rate-limit
"""
import time
import random

def calcular_delay_jitter(tamanho_mensagem):
    """
    Calcula um atraso não-linear baseado no tamanho da mensagem enviada,
    simulando o tempo de leitura humana e processamento mental antes de
    prosseguir para a próxima conversa.
    """
    # Tempo base para trocar de chat
    base_tempo = 5.0
    
    # Tempo estimado de leitura (aprox. 1 segundo para cada 20 caracteres)
    tempo_leitura = tamanho_mensagem / 20.0
    
    # Média (mu) e desvio padrão (sigma) para o atraso
    mu = base_tempo + tempo_leitura
    sigma = mu * 0.2  # 20% de variação (jitter)

    # Gera o tempo usando distribuição normal (Gaussiana)
    atraso_calculado = random.gauss(mu, sigma)
    
    # Garante um tempo mínimo e máximo razoável para evitar anomalias da curva
    atraso_final = max(8.0, min(atraso_calculado, 35.0))
    
    return atraso_final

class ControlePausasOperacionais:
    """
    Gerencia o estado da sessão de envios para introduzir 'Pausas Operacionais'
    (cool-down periods) baseadas no volume e no tempo, respeitando o rate limit.
    """
    def __init__(self):
        self.mensagens_enviadas_no_ciclo = 0
        self.limite_proxima_pausa = self._gerar_novo_limite()

    def _gerar_novo_limite(self):
        # Decide de forma orgânica que o "humano" vai pausar após 12 a 22 mensagens
        return random.randint(12, 22)

    def registrar_envio_e_verificar_pausa(self):
        """
        Registra o envio. Retorna um tempo de pausa longa (em segundos) se o limite
        foi atingido, ou 0 caso contrário.
        """
        self.mensagens_enviadas_no_ciclo += 1
        
        if self.mensagens_enviadas_no_ciclo >= self.limite_proxima_pausa:
            # Reseta o contador
            self.mensagens_enviadas_no_ciclo = 0
            self.limite_proxima_pausa = self._gerar_novo_limite()
            
            # Gera uma pausa longa entre 1.5 a 3.5 minutos (simulando beber água, responder outro chat real, etc)
            pausa_longa = random.uniform(90.0, 210.0)
            return pausa_longa
            
        return 0.0


def calcular_backoff_exponencial(tentativa: int, base_s: float = 30.0, fator: float = 2.0) -> float:
    """
    Padrão: Exponential Backoff com Jitter (tolerância a falhas - n8n 2026).
    Usado nas retentativas do Mission Control para evitar saturar a plataforma
    logo após uma falha de entrega.
    
    Fórmula: delay = base * (fator ^ tentativa) + ruído aleatório
    Exemplos: tentativa 1 → ~30s, tentativa 2 → ~60s, tentativa 3 → ~120s
    """
    delay_base = base_s * (fator ** (tentativa - 1))
    # Adiciona jitter de ±20% para quebrar o padrão de retry sincronizado
    jitter = delay_base * random.uniform(-0.20, 0.20)
    delay_final = delay_base + jitter
    # Teto máximo de 5 minutos para não travar demais
    return min(delay_final, 300.0)
