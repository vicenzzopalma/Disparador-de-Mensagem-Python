"""
dashboard.py
============
Padrão: "Observabilidade" (n8n 2026 Best Practices)
- Dashboard em tempo real no terminal
- Exibe métricas de sessão: enviados, falhas, velocidade, tempo restante estimado
- Painel "Mission Control" para visão geral do estado da automação
"""
import time
import datetime


class SessionDashboard:
    """
    Dashboard de observabilidade em tempo real exibido no terminal.
    Baseado no conceito de 'Dashboard Agente de IA' encontrado nos templates da comunidade.
    """

    def __init__(self, total_numeros: int):
        self.total = total_numeros
        self.enviados = 0
        self.falhas = 0
        self.pulados = 0
        self.inicio_sessao = time.time()
        self.historico_tempos: list[float] = []  # Histórico de tempo por envio para calcular média

    def registrar_envio(self, duracao_envio_s: float):
        self.enviados += 1
        self.historico_tempos.append(duracao_envio_s)
        # Mantém apenas os últimos 10 para média móvel (mais preciso que a média total)
        if len(self.historico_tempos) > 10:
            self.historico_tempos.pop(0)

    def registrar_falha(self):
        self.falhas += 1

    def registrar_pulado(self):
        self.pulados += 1

    def _calcular_eta(self) -> str:
        """Calcula o tempo estimado para conclusão (ETA) com base na velocidade atual."""
        restantes = self.total - self.enviados - self.falhas - self.pulados
        if not self.historico_tempos or restantes <= 0:
            return "Calculando..."
        
        media_por_envio = sum(self.historico_tempos) / len(self.historico_tempos)
        segundos_restantes = restantes * media_por_envio
        
        horas = int(segundos_restantes // 3600)
        minutos = int((segundos_restantes % 3600) // 60)
        segundos = int(segundos_restantes % 60)
        
        if horas > 0:
            return f"{horas}h {minutos}m {segundos}s"
        elif minutos > 0:
            return f"{minutos}m {segundos}s"
        else:
            return f"{segundos}s"

    def _tempo_decorrido(self) -> str:
        decorrido = time.time() - self.inicio_sessao
        horas = int(decorrido // 3600)
        minutos = int((decorrido % 3600) // 60)
        segundos = int(decorrido % 60)
        if horas > 0:
            return f"{horas}h {minutos}m {segundos}s"
        return f"{minutos}m {segundos}s"

    def _velocidade(self) -> str:
        decorrido = time.time() - self.inicio_sessao
        if decorrido < 1 or self.enviados == 0:
            return "N/A"
        msgs_por_hora = (self.enviados / decorrido) * 3600
        return f"{msgs_por_hora:.1f} msg/h"

    def _barra_progresso(self, largura: int = 30) -> str:
        processados = self.enviados + self.falhas + self.pulados
        percentual = processados / self.total if self.total > 0 else 0
        preenchido = int(largura * percentual)
        barra = "█" * preenchido + "░" * (largura - preenchido)
        return f"[{barra}] {percentual*100:.1f}%"

    def imprimir(self, numero_atual: str = "", acao: str = ""):
        """Imprime o painel de status atual no terminal."""
        processados = self.enviados + self.falhas + self.pulados
        linha_sep = "=" * 60

        print(f"\n{linha_sep}")
        print(f"  [MISSION CONTROL] - PAINEL DE OPERACOES")
        print(linha_sep)
        print(f"  Tempo decorrido : {self._tempo_decorrido():<15} ETA: {self._calcular_eta()}")
        print(f"  Progresso       : {self._barra_progresso()}")
        print(f"  -----------------------------------------------------")
        print(f"  Enviados  : {self.enviados:<5}  Falhas: {self.falhas:<5}  Pulados: {self.pulados}")
        print(f"  Total     : {processados}/{self.total:<5}  Velocidade: {self._velocidade()}")
        if numero_atual:
            print(f"  -----------------------------------------------------")
            print(f"  Atual     : {numero_atual}")
        if acao:
            print(f"  Acao      : {acao}")
        print(f"{linha_sep}\n")

    def imprimir_resumo_final(self, resumo_mc: dict):
        """Imprime o relatório final da sessão."""
        linha_sep = "=" * 60
        print(f"\n{linha_sep}")
        print(f"  SESSAO FINALIZADA - RELATORIO COMPLETO")
        print(linha_sep)
        print(f"  Mensagens entregues : {self.enviados}")
        print(f"  Falhas persistidas  : {resumo_mc['na_dead_letter_queue']}")
        print(f"  Pulados (ja tinham) : {self.pulados}")
        print(f"  Tempo total          : {self._tempo_decorrido()}")
        print(f"  Velocidade media     : {self._velocidade()}")
        print(f"  -----------------------------------------------------")
        if resumo_mc['na_dead_letter_queue'] > 0:
            print(f"  Atenção: {resumo_mc['na_dead_letter_queue']} numero(s) na Dead-Letter Queue.")
            print(f"       Arquivo: {resumo_mc['arquivo_falhas']}")
            print(f"       Execute o script novamente para tentar reprocessá-los.")
        print(f"  Log completo salvo em: {resumo_mc['arquivo_log']}")
        print(f"{linha_sep}\n")
