Viewed motor_semantico.py:1-31

```markdown
# 🚀 WhatsApp Multi-Account Agent (Resilience 2026 Edition)

Este projeto é um ecossistema avançado de automação para WhatsApp Web, projetado para operar com múltiplas contas simultâneas, alta variação linguística e comportamento humano simulado (HCI - Human-Computer Interaction). 

Diferente de scripts de disparo lineares, este sistema utiliza uma arquitetura **Orchestrator-Worker** inspirada nos padrões de automação de 2026, garantindo resiliência, observabilidade e escalabilidade.

---

## 🌟 Diferenciais Tecnológicos

### 1. Orquestração Multi-Conta
- **Paralelismo Real**: O `orquestrador.py` divide a carga de trabalho entre múltiplas contas de WhatsApp, lançando workers independentes em processos isolados.
- **Isolamento de Perfis**: Cada conta mantém sua própria sessão de Chrome (`user-data-dir`), eliminando a necessidade de escanear o QR Code a cada execução.

### 2. Motor de Inteligência Semântica
- **Estrutura Dinâmica**: Geração de mensagens baseada em dicionários cruzados (Abertura, Motivo, Objetivo, Benefício), garantindo que mensagens consecutivas nunca sejam idênticas.
- **Contexto Temporal**: Saudações inteligentes que se ajustam automaticamente ao período do dia (Manhã, Tarde, Noite).
- **Edge-ACK**: Pré-geração de todo o lote de mensagens antes do início do disparo, eliminando latência de processamento durante a operação crítica do navegador.

### 3. Cadência Humana e Resiliência
- **Jitter Gaussiano**: Delays de envio baseados em distribuição normal, simulando o tempo variável de leitura e reflexão de um humano.
- **Pausas Operacionais**: Ciclos de pausa orgânica (cool-down) para respeitar limites de taxa e simular comportamentos naturais.
- **Backoff Exponencial**: Sistema de retentativa inteligente que aumenta o tempo de espera progressivamente após falhas de rede.

### 4. Mission Control & Observabilidade
- **Dead-Letter Queue (DLQ)**: Números com falhas persistentes são automaticamente movidos para uma "Fila de Mensagens Mortas" (`falhas.txt`) para reprocessamento manual ou posterior.
- **Dashboards em Tempo Real**: Interface de terminal com barra de progresso, velocidade de envio (msg/h) e cálculo de ETA (Tempo Estimado de Conclusão).
- **Log Estruturado**: Auditoria completa da sessão em formato JSONL para análise de dados e performance.

---

## 🏗️ Arquitetura do Projeto

O sistema é dividido em módulos especializados:

- `orquestrador.py`: Gerenciador central que divide a lista e coordena os workers.
- `worker.py`: O "braço executor" que controla a instância do Selenium e interage com o WhatsApp.
- `motor_semantico.py`: O "cérebro" linguístico que compõe as variações de texto.
- `cadencia.py`: O motor de tempo e simulador de comportamento humano.
- `mission_control.py`: O sistema de segurança e tratamento centralizado de erros.
- `dashboard.py`: O painel de visualização de métricas da sessão.
- `lista_numeros.py`: Fonte centralizada da base de dados de contatos.

---

## 🚀 Como Executar

1. **Configuração**: Adicione suas contas no arquivo `orquestrador.py`:
   ```python
   CONTAS = [
       {"id": "CONTA_01", "perfil": "perfil_01"},
       {"id": "CONTA_02", "perfil": "perfil_02"}
   ]
   ```
2. **Dependências**:
   ```bash
   pip install selenium undetected-chromedriver
   ```
3. **Início**:
   ```bash
   python orquestrador.py
   ```

---

## ⚠️ Requisitos de Sistema
- **Chrome / Brave Browser** instalado.
- **Hardware**: Recomendado 4GB de RAM livre por conta ativa (instâncias de Chrome). 
- *Otimizado para rodar em hardware de entrada (GPUs integradas e processadores modestos).*

---
> **Disclaimer**: Este projeto foi desenvolvido para fins de automação legítima e produtividade. O uso indevido para spam pode resultar no banimento das contas pelas diretrizes do WhatsApp.
```
Vicenzzo Palma Mastronikolis :)
