from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import subprocess
import threading
import time
import sys
from werkzeug.utils import secure_filename
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from image_utils import process_image_anti_ban
from lista_numeros import preparar_numeros

app = Flask(__name__, static_folder='static')
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global state to store campaign data and progress
campaign_state = {
    "status": "idle",
    "numbers": ["4899339439", "1139126105"], # Reduced default for code size, UI handles custom numbers
    "message_greeting": "{Olá|Oi|Opa|Tudo bem?|Como vai?|Salve|Oi tudo bem?|Opa, tudo certo?|E aí|Ei}, {{saudacao_temporal}}",
    "message_body": "{Somos da Realess|Aqui é da equipe Realess|Representamos a Realess|Pela Realess}, {responsáveis pela cobrança|cuidamos da gestão financeira|fazendo o controle de boletos|gestores de cobrança} da Seara. {A pedido do administrativo|Por orientação da gestão|Seguindo o direcionamento administrativo|Por solicitação interna}, criamos este grupo para {agilizar o envio de boletos|facilitar o contato|resolver pendências mais rápido|dar suporte financeiro}.\n\n{Acesse o grupo pelo link|Link do grupo oficial|Entre no grupo aqui}: https://chat.whatsapp.com/Js3QrauU3Y7ECPh6VWzXcN",
    "image_path": None,
    "accounts": [
        {"id": "CONTA_01", "perfil": "wpp_perfil_01", "active": True, "connected": False, "status_label": "Carregando"},
        {"id": "CONTA_02", "perfil": "wpp_perfil_02", "active": False, "connected": False, "status_label": "Carregando"}
    ],
    "progress": {},
    "logs": []
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REALEZA_DIR = BASE_DIR
MEMORIA_FILE = os.path.join(REALEZA_DIR, "ja_enviados.txt")

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/daemon_status', methods=['POST'])
def daemon_status():
    data = request.json
    conta_id = data.get("conta_id")
    status = data.get("status")
    
    for acc in campaign_state["accounts"]:
        if acc["id"] == conta_id:
            acc["status_label"] = status
            if status == "Conectado":
                acc["connected"] = True
            else:
                acc["connected"] = False
    return jsonify({"status": "ok"})


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        campaign_state["numbers"] = data.get("numbers", [])
        campaign_state["message_greeting"] = data.get("message_greeting", "")
        campaign_state["message_body"] = data.get("message_body", "")
        incoming_accounts = data.get("accounts", [])
        if incoming_accounts:
            # Update only active property from UI, keep connected and status_label from internal state
            for i_acc in incoming_accounts:
                for c_acc in campaign_state["accounts"]:
                    if i_acc["id"] == c_acc["id"]:
                        c_acc["active"] = i_acc.get("active", False)
        return jsonify({"status": "success"})
    
    if not campaign_state["accounts"]:
        campaign_state["accounts"] = [
            {"id": "CONTA_01", "perfil": "wpp_perfil_01", "active": True, "connected": False, "status_label": "Carregando"},
            {"id": "CONTA_02", "perfil": "wpp_perfil_02", "active": False, "connected": False, "status_label": "Carregando"}
        ]
        
    return jsonify({
        "numbers": campaign_state["numbers"],
        "message_greeting": campaign_state["message_greeting"],
        "message_body": campaign_state["message_body"],
        "accounts": campaign_state["accounts"],
        "image_path": campaign_state["image_path"]
    })

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)
    
    processed_path = process_image_anti_ban(temp_path, app.config['UPLOAD_FOLDER'])
    campaign_state["image_path"] = os.path.abspath(processed_path)
    
    return jsonify({"status": "success", "path": processed_path})

@app.route('/api/connect', methods=['POST'])
def connect_account():
    data = request.json
    conta_id = data.get("id")
    if not conta_id: return jsonify({"error": "Missing ID"}), 400
    
    diretorio_conta = os.path.join(REALEZA_DIR, f"dados_{conta_id}")
    os.makedirs(diretorio_conta, exist_ok=True)
    
    with open(os.path.join(diretorio_conta, "cmd_show.json"), "w") as f:
        json.dump({"action": "show"}, f)
        
    return jsonify({"status": "show_requested"})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": campaign_state["status"],
        "progress": campaign_state["progress"],
        "logs": campaign_state["logs"][-50:],
        "accounts": campaign_state["accounts"]
    })

@app.route('/api/pause', methods=['POST'])
def pause_campaign():
    if campaign_state["status"] == "running":
        campaign_state["status"] = "paused"
        campaign_state["logs"].append("⏳ Campanha pausada pelo usuário.")
        for acc in campaign_state["accounts"]:
            dir_c = os.path.join(REALEZA_DIR, f"dados_{acc['id']}")
            if os.path.exists(dir_c):
                with open(os.path.join(dir_c, "cmd_pause.json"), "w") as f: json.dump({}, f)
        return jsonify({"status": "paused"})
    elif campaign_state["status"] == "paused":
        campaign_state["status"] = "running"
        campaign_state["logs"].append("▶️ Campanha retomada.")
        for acc in campaign_state["accounts"]:
            dir_c = os.path.join(REALEZA_DIR, f"dados_{acc['id']}")
            try: os.remove(os.path.join(dir_c, "cmd_pause.json"))
            except: pass
        return jsonify({"status": "resumed"})
    return jsonify({"error": "Campaign not running"}), 400

@app.route('/api/stop', methods=['POST'])
def stop_campaign():
    campaign_state["status"] = "finished"
    campaign_state["logs"].append("🛑 Campanha interrompida pelo usuário.")
    
    for acc in campaign_state["accounts"]:
        dir_c = os.path.join(REALEZA_DIR, f"dados_{acc['id']}")
        if os.path.exists(dir_c):
            with open(os.path.join(dir_c, "cmd_stop.json"), "w") as f: json.dump({}, f)
            try: os.remove(os.path.join(dir_c, "cmd_pause.json"))
            except: pass
            try: os.remove(os.path.join(dir_c, "cmd_send.json"))
            except: pass
            
    return jsonify({"status": "stopped"})

@app.route('/api/start', methods=['POST'])
def start_campaign():
    if campaign_state["status"] == "running":
        return jsonify({"error": "Campaign already running"}), 400
    
    campaign_state["status"] = "running"
    campaign_state["progress"] = {}
    campaign_state["logs"].append("🚀 Iniciando campanha... Escrevendo payloads para os daemons.")
    
    thread = threading.Thread(target=run_orchestrator)
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/report_progress', methods=['POST'])
def report_progress():
    data = request.json
    conta_id = data.get("conta_id")
    if conta_id:
        campaign_state["progress"][conta_id] = data.get("stats")
        if data.get("log"):
            campaign_state["logs"].append(f"[{conta_id}] {data.get('log')}")
    
    if "Concluido" in data.get("action", "") or "finalizada" in data.get("log", ""):
        pass

    return jsonify({"status": "ok"})

def kill_existing_daemons():
    import subprocess
    try:
        # Clear command files
        for acc in campaign_state["accounts"]:
            dir_c = os.path.join(REALEZA_DIR, f"dados_{acc['id']}")
            if os.path.exists(dir_c):
                for f_name in ["cmd_send.json", "cmd_stop.json", "cmd_pause.json", "cmd_show.json"]:
                    f_path = os.path.join(dir_c, f_name)
                    if os.path.exists(f_path):
                        try: os.remove(f_path)
                        except: pass

        if os.name == 'nt':
            ps_cmd = '& { Get-CimInstance Win32_Process -Filter "CommandLine like \'%wpp_perfil%\'" | ForEach-Object { Stop-Process $_.ProcessId -Force } }'
            subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], capture_output=True)
        else:
            subprocess.run("pkill -f wpp_perfil", shell=True, capture_output=True)
    except Exception as e:
        print(f"Erro ao limpar daemons antigos: {e}")

@app.route('/api/reload_daemons', methods=['POST'])
def reload_daemons():
    global daemons
    kill_existing_daemons()
    daemons.clear()
    
    for acc in campaign_state["accounts"]:
        acc["status_label"] = "Carregando"
        cmd = [
            sys.executable, os.path.join(REALEZA_DIR, "daemon_worker.py"),
            "--conta-id", acc["id"],
            "--perfil", acc["perfil"],
            "--status-url", "http://127.0.0.1:5005/api/daemon_status"
        ]
        p = subprocess.Popen(cmd, cwd=REALEZA_DIR, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        daemons.append(p)
        campaign_state["logs"].append(f"🔄 Daemon {acc['id']} recarregado.")
        time.sleep(5)
        
    return jsonify({"status": "reloaded"})

def run_orchestrator():
    try:
        ja_enviados = set()
        if os.path.exists(MEMORIA_FILE):
            with open(MEMORIA_FILE, "r") as f:
                for line in f:
                    l = line.strip()
                    if l:
                        if len(l) in (10, 11) and not l.startswith('55'): l = '55' + l
                        ja_enviados.add(l)
        
        campaign_numbers_raw = "\n".join(campaign_state["numbers"])
        normalized_campaign_numbers = preparar_numeros(campaign_numbers_raw)
        filtered_numbers = [n for n in normalized_campaign_numbers if n not in ja_enviados]
        
        if not filtered_numbers:
            campaign_state["status"] = "finished"
            campaign_state["logs"].append("✅ Todos os números já foram enviados.")
            return

        active_accounts = [a for a in campaign_state["accounts"] if a.get("active")]
        if not active_accounts:
            campaign_state["status"] = "idle"
            campaign_state["logs"].append("❌ Nenhuma conta ativa selecionada.")
            return

        import math
        tamanho = math.ceil(len(filtered_numbers) / len(active_accounts))
        partes = [filtered_numbers[i:i + tamanho] for i in range(0, len(filtered_numbers), tamanho)]
        
        files_written = []

        for i, conta in enumerate(active_accounts):
            if i >= len(partes): break
            
            numeros_conta = partes[i]
            diretorio_conta = os.path.join(REALEZA_DIR, f"dados_{conta['id']}")
            os.makedirs(diretorio_conta, exist_ok=True)
            
            full_message = f"{campaign_state['message_greeting']}\n\n{campaign_state['message_body']}".strip()
            
            payload = {
                "numeros": numeros_conta,
                "mensagem": full_message,
                "imagem": campaign_state["image_path"],
                "arquivo_memoria": MEMORIA_FILE,
                "ui_report_url": "http://127.0.0.1:5005/api/report_progress"
            }
            
            cmd_file = os.path.join(diretorio_conta, "cmd_send.json")
            with open(cmd_file, "w") as f:
                json.dump(payload, f)
            files_written.append(cmd_file)
            campaign_state["logs"].append(f"✅ Payload entregue para o Daemon da {conta['id']}.")

        # Esperar até que todos os daemons tenham deletado seus arquivos cmd_send.json (significa que terminaram)
        while True:
            if campaign_state["status"] != "running":
                break
            all_done = True
            for cf in files_written:
                if os.path.exists(cf):
                    all_done = False
                    break
            if all_done:
                break
            time.sleep(3)
        
        if campaign_state["status"] != "stopped":
            campaign_state["status"] = "finished"
            campaign_state["logs"].append("🏁 Campanha finalizada.")

    except Exception as e:
        campaign_state["status"] = "idle"
        campaign_state["logs"].append(f"❌ Erro no orquestrador: {str(e)}")

# Daemon launcher
daemons = []
def launch_daemons():
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        kill_existing_daemons()
        for acc in campaign_state["accounts"]:
            cmd = [
                sys.executable, os.path.join(REALEZA_DIR, "daemon_worker.py"),
                "--conta-id", acc["id"],
                "--perfil", acc["perfil"],
                "--status-url", "http://127.0.0.1:5005/api/daemon_status"
            ]
            # Use subprocess to run without blocking, hidden window if possible
            p = subprocess.Popen(cmd, cwd=REALEZA_DIR, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            daemons.append(p)
            print(f"Lançado Daemon para {acc['id']}")
            time.sleep(5)

if __name__ == '__main__':
    launch_daemons()
    try:
        app.run(host='127.0.0.1', port=5005, debug=True)
    finally:
        for p in daemons:
            p.terminate()
