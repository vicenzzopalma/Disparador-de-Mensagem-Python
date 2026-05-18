"""
mission_control.py
==================
Padrão: "Mission Control" (n8n 2026 Best Practices)
- Tratamento centralizado de erros de toda a sessão
- Dead-Letter Queue: números que falharam vão para 'falhas.txt' para reprocessamento posterior
- Retry Queue: controla quantas tentativas cada número já teve
- Log estruturado de eventos com timestamp para auditoria
"""
import os
import json
import datetime


class MissionControl:
    """
    Núcleo central de tratamento de erros, reprocessamento e auditoria.
    Inspirado no padrão 'Error Trigger + Dead-Letter Queue' do n8n 2026.
    """

    def __init__(self, diretorio_base: str):
        self.diretorio_base = diretorio_base
        self.arquivo_falhas = os.path.join(diretorio_base, "falhas.txt")
        self.arquivo_log = os.path.join(diretorio_base, "log_sessao.jsonl")
        self.fila_retry: dict[str, int] = {}  # numero -> quantidade de tentativas
        self.MAX_TENTATIVAS = 2

        # Carrega falhas anteriores (números que nunca foram entregues)
        self._carregar_falhas_pendentes()

    def _carregar_falhas_pendentes(self):
        """Lê o arquivo de falhas anteriores para popular a fila de retry."""
        if os.path.exists(self.arquivo_falhas):
            with open(self.arquivo_falhas, "r") as f:
                for linha in f:
                    numero = linha.strip()
                    if numero:
                        # Marca como 1 tentativa já feita (da sessão anterior)
                        self.fila_retry[numero] = 1

    def registrar_falha(self, numero: str, motivo: str):
        """
        Registra uma falha de envio. Se o número atingiu o limite de retentativas,
        ele vai para a Dead-Letter Queue (falhas.txt). Caso contrário, é marcado para retry.
        """
        tentativas = self.fila_retry.get(numero, 0) + 1
        self.fila_retry[numero] = tentativas

        self._log_evento("FALHA", numero, {"motivo": motivo, "tentativa": tentativas})

        if tentativas >= self.MAX_TENTATIVAS:
            # Número entrou na Dead-Letter Queue
            self._escrever_dead_letter(numero)
            self._log_evento("DLQ", numero, {"status": "Adicionado à Dead-Letter Queue após esgotamento de retentativas"})
            return False  # Sem mais retentativas
        
        return True  # Há retentativas disponíveis

    def registrar_sucesso(self, numero: str):
        """Remove o número da fila de falhas quando o envio for bem-sucedido."""
        # Se estava na lista de retries, remove pois agora foi entregue
        if numero in self.fila_retry:
            del self.fila_retry[numero]
        
        # Remove da Dead-Letter Queue se estava lá
        self._remover_da_dead_letter(numero)
        self._log_evento("SUCESSO", numero, {})

    def _escrever_dead_letter(self, numero: str):
        """Persiste o número na Dead-Letter Queue no disco."""
        # Lê os existentes para não duplicar
        existentes = set()
        if os.path.exists(self.arquivo_falhas):
            with open(self.arquivo_falhas, "r") as f:
                existentes = set(l.strip() for l in f if l.strip())
        
        if numero not in existentes:
            with open(self.arquivo_falhas, "a") as f:
                f.write(f"{numero}\n")

    def _remover_da_dead_letter(self, numero: str):
        """Remove o número da Dead-Letter Queue quando for entregue com sucesso."""
        if not os.path.exists(self.arquivo_falhas):
            return
        with open(self.arquivo_falhas, "r") as f:
            linhas = [l.strip() for l in f if l.strip() and l.strip() != numero]
        with open(self.arquivo_falhas, "w") as f:
            f.write("\n".join(linhas) + "\n" if linhas else "")

    def _log_evento(self, tipo: str, numero: str, dados: dict):
        """Registra um evento estruturado em JSONL para auditoria posterior."""
        evento = {
            "timestamp": datetime.datetime.now().isoformat(),
            "tipo": tipo,
            "numero": numero,
            **dados
        }
        with open(self.arquivo_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def obter_numeros_para_retry(self) -> list[str]:
        """Retorna a lista de números que ainda têm retentativas disponíveis."""
        return [n for n, t in self.fila_retry.items() if t < self.MAX_TENTATIVAS]

    def resumo_final(self) -> dict:
        """Retorna um resumo do estado final da sessão."""
        dlq_count = 0
        if os.path.exists(self.arquivo_falhas):
            with open(self.arquivo_falhas, "r") as f:
                dlq_count = sum(1 for l in f if l.strip())
        
        return {
            "na_dead_letter_queue": dlq_count,
            "arquivo_falhas": self.arquivo_falhas,
            "arquivo_log": self.arquivo_log
        }
