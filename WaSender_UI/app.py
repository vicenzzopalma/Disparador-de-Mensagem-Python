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
    "numbers": ["4899339439", "1139126105", "1139126105", "1139126160", "11911454138", "11911454138", "11911841946", "11911841946", "11916527751", "11916617725", "11916617725", "11916648609", "11916648609", "11930525665", "11930525665", "11930709110", "11930709110", "11932793176", "11932793176", "11932794070", "11934992654", "11937709037", "11937709037", "11941551087", "11941551087", "11941836612", "11943108539", "11943690969", "11943690969", "11944455150", "11944988598", "11945342155", "11945342155", "11945777535", "11950467908", "11950467908", "11950803038", "11950803038", "11953072096", "11953072096", "11955878021", "11956846257", "11957851283", "11959253755", "11959253755", "11961716441", "11963018001", "11963018001", "11963368292", "11963394795", "11963811441", "11963875632", "11964704725", "11966004147", "11966004147", "11966026178", "11966026178", "11966509642", "11968814045", "11968814045", "11969210305", "11969210305", "11969286281", "11969298056", "11969298056", "11970791521", "11970791521", "11971162545", "11971807784", "11972790690", "11972823176", "11972823176", "11973983710", "11974514287", "11974514287", "11975520967", "11975538794", "11975564361", "11975564361", "11976419743", "11976419743", "11976428553", "11976428553", "11976491558", "11976491558", "11981582332", "11985325252", "11986737268", "11986737956", "11987391893", "11989020219", "11989021464", "11989324276", "11989328817", "11989369475", "11989369475", "11989779557", "11989869151", "11989869151", "11989871434", "11991562492", "11992438152", "11992438152", "11992461022", "11992561390", "11992561390", "11992576812", "11992697475", "11992697475", "11992968465", "11993277455", "11993290222", "11993498769", "11994224627", "11994224627", "11995467549", "11995467549", "11996959618", "11997012159", "11997012159", "11997288879", "11997288879", "11998393558", "11998764697", "11998764697", "11998949059", "11999431845", "11999431845", "12981058496", "12991701306", "12991992084", "12991992084", "12996009562", "12996097492", "12996097492", "12996177034", "12997309175", "12997309175", "12997463119", "12997463119", "13974065359", "13981111274", "13996312677", "13996365440", "13996365440", "13996434911", "13996434911", "13996599961", "13996599961", "13997086989", "13997281538", "13997281538", "13997567986", "14981113488", "14981113488", "14996046167", "14996229878", "14996229878", "14996866474", "14997062856", "14997682934", "14998224306", "14998266185", "14998486074", "14998486074", "15991285224", "15991285224", "15991797686", "15991797686", "15991798748", "15996195994", "15996195994", "15996300915", "15996408914", "15998539182", "15998539628", "16981164169", "16981164169", "16981601313", "16981601313", "16981603337", "16991993149", "16991993149", "16992368930", "16992368930", "16992531723", "16992531723", "16996114612", "16996114612", "16996323601", "16996323601", "16997102817", "16997102817", "16997268575", "16997268575", "16997599732", "16997615816", "16997615816", "16997638305", "16997733576", "16997913165", "17991438244", "17991439081", "17991566949", "17996066914", "17996475470", "17996475470", "17996520554", "18981149008", "18991976851", "1938678058", "19971001680", "19971023614", "19971023614", "19971677844", "19971677844", "19981110568", "19981110677", "19981110677", "19992592732", "19994001773", "19994008135", "19994008135", "19994729899", "19994860295", "19996444874", "19997399291", "19997622871", "19997622871", "19997814653", "19997814653", "19998047107", "19999438681", "19999438681", "19999650861", "21964564800", "21967034459", "21967034585", "21967225411", "21967225411", "21967225431", "21967231963", "21972291976", "21972291976", "21972308929", "21972593791", "21972635405", "21973388922", "21973481100", "21975807334", "21975807334", "21976885453", "21976928343", "21976928343", "21976928591", "21976928591", "21979542215", "21980051771", "21981184435", "21992530236", "21992530236", "21992584344", "21993425901", "21993502550", "21995604807", "21995718869", "21996220512", "21996220512", "21996302386", "21996304210", "21996304210", "21996316751", "21996397508", "21996405251", "21996405517", "21996709237", "21996768634", "21996825727", "21996917248", "21996986994", "21998237657", "22981008483", "22981460925", "22992584728", "22992790495", "22998026575", "22998026575", "22998499639", "22999552639", "22999827320", "24992900556", "24993157530", "24998138885", "24998794765", "24999375564", "24999375564", "24999659193", "27981820187", "27992297523", "27992395653", "27992919096", "27995226622", "27996527860", "27998231892", "31971515950", "31971515950", "31971837478", "31971837478", "31971849813", "31983145680", "31983405131", "31983405131", "31983491478", "3198362197", "3198362197", "31984102361", "31984102361", "31984165040", "31984165040", "31991965078", "31992933522", "31995319215", "31995530423", "31995928581", "31996040478", "31996040478", "31996146020", "31996146020", "31996716497", "31996766825", "31997128590", "31997949291", "31997969204", "31999430423", "31999430423", "32998121584", "32998121584", "32999002612", "32999002612", "32999046530", "32999548924", "32999548924", "32999740580", "32999740580", "34984036396", "34991946659", "34991946659", "34998074933", "34998078132", "34998122943", "34998122943", "34998274273", "34998386940", "34998386940", "34999027748", "34999027748", "34999280225", "34999280225", "34999290494", "34999290494", "34999383706", "34999383706", "34999419095", "34999554786", "34999839302", "34999849313", "34999849313", "34999863552", "34999863552", "35984138877", "35997807249", "35997807249", "35998000258", "35998095280", "37998468940", "37998757512", "38997255571", "38997255571", "41987588907", "41987601773", "41987975592", "41988736954", "41988822486", "41988901457", "41991220985", "41991896799", "41992011072", "41992668386", "41992699359", "41992768549", "41996159005", "41998051359", "4321015550", "43988059952", "43991106423", "43991555833", "43991562318", "43999875800", "4499122672", "44998001047", "44998001047", "473447818", "4792380442", "47991010340", "47991156112", "47991156112", "47992201746", "47992201746", "47992334792", "47992384359", "47992384359", "47992432576", "47992897372", "47996314349", "47999236988", "47999236988", "4888632640", "4888632640", "4891119234", "4898661737", "48988008148", "48988419586", "48991265975", "4899345111", "4899891177", "49991861259", "4999833374", "5181311232", "5197527782", "51980158374", "51980265139", "51980265139", "51980388354", "51980388354", "51980389826", "51981196484", "51981624674", "51991903257", "51993197584", "51993805970", "51995079436", "51995079436", "51995304494", "51995375551", "51995375551", "51995395642", "51995704696", "51996537919", "51996580793", "51997639225", "51997672340", "51997680903", "51998039767", "51999137540", "5391032945", "5391568939", "53999616010", "53999616010", "5484170809", "5491907330", "54981127571", "54991187870", "54996934610", "54999256781", "54999306891", "54999382118", "5534126997", "55997262450", "56275196149", "6192955267", "61981348938", "61981356906", "61981530392", "61981530457", "61981531412", "61981750038", "61981750091", "6198512235", "61991100005", "61991783568", "61992956003", "61993500373", "61993728100", "61993728100", "61993746228", "61993892422", "61993892422", "61995056924", "61996346724", "61998165823", "61998251314", "61998328160", "61998328308", "61998514749", "61998514749", "61998579546", "61999466361", "61999466361", "6292098989", "62981189447", "62981680546", "62981731662", "62981731662", "62993109602", "62994306970", "62994308472", "62996243368", "62998243794", "62998267294", "62998388713", "62998388713", "62998456104", "62999146449", "62999205604", "62999469688", "64992589168", "64993137868", "6499559621", "64996145648", "64996145648", "64999538284", "64999652320", "65981151642", "65992134955", "65992183570", "65993386406", "65996339016", "65998153856", "6599872179", "66992020384", "66992372615", "66996148593", "66996304761", "66996308385", "66996434857", "66996438154", "66996578680", "66996873576", "66996873576", "66997220582", "67981380963", "67991436838", "67992038044", "67992472821", "67992596708", "67992851291", "67992872733", "67993100912", "67996015592", "67998411054", "67999488076", "71981045502", "71981058910", "71981058910", "71981145497", "71981145497", "71981153793", "71981226967", "71981241209", "71981371033", "71981924442", "71984520200", "71991019624", "71991031984", "71991031984", "71991819558", "71996155363", "71996159332", "71996173303", "71996179128", "71996205189", "71996205189", "71996323968", "71996326543", "71996407690", "71996536324", "71996885600", "71996890728", "71996890728", "71996892267", "71997231040", "71997250886", "7199905551", "71999298926", "71999298926", "71999596874", "71999696048", "73981049970", "73981918070", "73982044733", "73982254942", "73982266683", "73991300807", "73991300807", "73991541020", "73998040352", "73998641548", "73998666547", "73999338517", "73999338517", "74981228011", "74981374244", "74981374244", "74981380274", "74998069470", "74999168196", "74999212128", "74999426770", "75981010386", "75981010386", "75981127313", "75981160551", "75981221404", "75981501792", "75981659715", "75981661063", "75982221285", "75982367382", "75983152301", "75991100004", "75991561009", "75991916944", "75991916944", "75992300403", "75997094255", "75997094255", "75998360926", "75998436494", "75998643554", "75998806936", "75999270945", "75999621533", "77981016522", "77981123672", "77981147364", "77981377467", "77991740011", "77991940087", "77998346622", "77998664632", "77998674576", "77999137633", "77999690196", "77999838708", "8006434950", "81981404167", "81981404167", "81981478744", "81981572716", "81981572716", "81982269825", "81982269825", "81982413594", "81982438328", "81982573541", "81982573541", "81989740044", "81989740044", "81991409246", "81991625516", "81991625516", "81991699881", "81991699881", "81992292022", "81992543295", "81992543295", "81992634023", "81992634023", "81992701442", "81992701442", "81992899806", "81992899806", "81994038944", "81996316758", "81998533837", "81998533837", "81998533888", "81999211359", "81999872365", "81999872365", "82982299181", "82982301908", "82982301908", "83981052164", "83981052164", "83981961476", "83991432596", "83991432596", "84991493033", "84991798481", "84999872797", "84999872797", "85981030170", "85981300322", "85981332677", "85981332677", "85981535167", "85981648367", "85981867531", "85982149786", "85992499185", "85992633325", "85999223900", "85999223900", "87991047400", "87991047400", "87991577649", "88981033874", "88981033874", "88981033936", "88981125499", "88981125499", "88981199251", "88981199251", "88981291386", "88981303411", "88981303411", "88981311527", "88981311527", "88981330651", "88981345229", "88981362628", "88981362628", "88992084585", "88992084585", "88992525398", "88994770032", "91991231173", "91991557866", "91991936782", "91992063649", "91992454764", "91992454764", "91992626841", "91992693342", "92984435594", "92994826446", "96992059406", "974908260", "99844-7982"],
    "message_greeting": "{Olá|Oi|Opa|Tudo bem?|Como vai?|Salve|Oi tudo bem?|Opa, tudo certo?|E aí|Ei}, {{saudacao_temporal}}",
    "message_body": "{Somos da Realess|Aqui é da equipe Realess|Representamos a Realess|Pela Realess}, {responsáveis pela cobrança|cuidamos da gestão financeira|fazendo o controle de boletos|gestores de cobrança} da Seara. {A pedido do administrativo|Por orientação da gestão|Seguindo o direcionamento administrativo|Por solicitação interna}, criamos este grupo para {agilizar o envio de boletos|facilitar o contato|resolver pendências mais rápido|dar suporte financeiro}.\n\n{Acesse o grupo pelo link|Link do grupo oficial|Entre no grupo aqui}: https://chat.whatsapp.com/Js3QrauU3Y7ECPh6VWzXcN",
    "image_path": None,
    "accounts": [
        {"id": "CONTA_01", "perfil": "wpp_perfil_01", "active": True, "connected": False},
        {"id": "CONTA_02", "perfil": "wpp_perfil_02", "active": False, "connected": False}
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

def check_account_connection(perfil_name):
    # Caminho do perfil dentro de RealezaSender
    perfil_path = os.path.join(REALEZA_DIR, perfil_name)
    # Verifica se existe a pasta IndexedDB do WhatsApp Web
    # No Windows, o Chrome salva em Default/IndexedDB ou diretamente na raiz do perfil se for um user-data-dir simples
    db_paths = [
        os.path.join(perfil_path, "Default", "IndexedDB", "https_web.whatsapp.com_0.indexeddb.leveldb"),
        os.path.join(perfil_path, "IndexedDB", "https_web.whatsapp.com_0.indexeddb.leveldb")
    ]
    return any(os.path.exists(p) for p in db_paths)

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        campaign_state["numbers"] = data.get("numbers", [])
        campaign_state["message_greeting"] = data.get("message_greeting", "")
        campaign_state["message_body"] = data.get("message_body", "")
        campaign_state["accounts"] = data.get("accounts", campaign_state["accounts"])
        return jsonify({"status": "success"})
    
    # Update connection status before returning
    for acc in campaign_state["accounts"]:
        acc["connected"] = check_account_connection(acc["perfil"])
        
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
    
    # Process image for Anti-Ban
    processed_path = process_image_anti_ban(temp_path, app.config['UPLOAD_FOLDER'])
    campaign_state["image_path"] = os.path.abspath(processed_path)
    
    return jsonify({"status": "success", "path": processed_path})

@app.route('/api/connect', methods=['POST'])
def connect_account():
    data = request.json
    conta_id = data.get("id")
    perfil = data.get("perfil")
    
    if not conta_id or not perfil:
        return jsonify({"error": "Missing ID or Profile"}), 400

    # Launch worker in "Login Mode" (just opens the browser)
    cmd = [
        sys.executable, os.path.join(REALEZA_DIR, "worker.py"),
        "--conta-id", conta_id,
        "--perfil", perfil,
        "--numeros-json", os.path.join(REALEZA_DIR, "_empty.json"), # Dummy file
        "--arquivo-memoria", MEMORIA_FILE,
        "--login-only" # New flag for worker.py
    ]
    
    # Create empty dummy file if not exists
    empty_json = os.path.join(REALEZA_DIR, "_empty.json")
    if not os.path.exists(empty_json):
        with open(empty_json, "w") as f: json.dump([], f)
        
    subprocess.Popen(cmd, cwd=REALEZA_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
    return jsonify({"status": "launched"})

active_processes = [] # List to track running worker processes

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": campaign_state["status"],
        "progress": campaign_state["progress"],
        "logs": campaign_state["logs"][-50:]
    })

@app.route('/api/pause', methods=['POST'])
def pause_campaign():
    if campaign_state["status"] == "running":
        campaign_state["status"] = "paused"
        campaign_state["logs"].append("⏳ Campanha pausada pelo usuário.")
        # Workers check this state via report_progress or a shared file
        return jsonify({"status": "paused"})
    elif campaign_state["status"] == "paused":
        campaign_state["status"] = "running"
        campaign_state["logs"].append("▶️ Campanha retomada.")
        return jsonify({"status": "resumed"})
    return jsonify({"error": "Campaign not running"}), 400

@app.route('/api/stop', methods=['POST'])
def stop_campaign():
    campaign_state["status"] = "finished"
    campaign_state["logs"].append("🛑 Campanha interrompida pelo usuário.")
    
    # Kill all active processes
    for proc, _ in active_processes:
        try:
            proc.terminate()
            # On Windows, terminate might not be enough for subprocesses with consoles
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
        except:
            pass
    active_processes.clear()
    
    return jsonify({"status": "stopped"})

@app.route('/api/start', methods=['POST'])
def start_campaign():
    if campaign_state["status"] == "running":
        return jsonify({"error": "Campaign already running"}), 400
    
    campaign_state["status"] = "running"
    campaign_state["progress"] = {}
    campaign_state["logs"].append("🚀 Iniciando campanha...")
    
    # Start orchestration in a separate thread
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
    
    # Return current status (allows worker to know if it should pause)
    return jsonify({
        "status": campaign_state["status"]
    })

def run_orchestrator():
    global active_processes
    active_processes = []
    try:
        # ... existing logic ...
        ja_enviados = set()
        if os.path.exists(MEMORIA_FILE):
            with open(MEMORIA_FILE, "r") as f:
                for line in f:
                    l = line.strip()
                    if l:
                        if len(l) in (10, 11) and not l.startswith('55'):
                            l = '55' + l
                        ja_enviados.add(l)
        
        # Normalize campaign numbers before filtering
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

        # Divide numbers
        import math
        tamanho = math.ceil(len(filtered_numbers) / len(active_accounts))
        partes = [filtered_numbers[i:i + tamanho] for i in range(0, len(filtered_numbers), tamanho)]
        
        for i, conta in enumerate(active_accounts):
            if i >= len(partes): break
            
            numeros_conta = partes[i]
            temp_json = os.path.join(REALEZA_DIR, f"_ui_temp_{conta['id']}.json")
            with open(temp_json, "w") as f:
                json.dump(numeros_conta, f)
            
            # Combine Greeting and Body
            full_message = f"{campaign_state['message_greeting']}\n\n{campaign_state['message_body']}".strip()
            
            cmd = [
                sys.executable, os.path.join(REALEZA_DIR, "worker.py"),
                "--conta-id", conta["id"],
                "--perfil", conta["perfil"],
                "--numeros-json", temp_json,
                "--arquivo-memoria", MEMORIA_FILE,
                "--ui-report-url", "http://127.0.0.1:5005/api/report_progress"
            ]

            if campaign_state["image_path"]:
                cmd.extend(["--imagem", campaign_state["image_path"]])
            
            if full_message:
                cmd.extend(["--mensagem", full_message])
            
            proc = subprocess.Popen(cmd, cwd=REALEZA_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
            active_processes.append((proc, temp_json))
            campaign_state["logs"].append(f"✅ Worker {conta['id']} iniciado.")

        # Wait for all processes
        while any(p[0].poll() is None for p in active_processes):
            time.sleep(2)
        
        # Cleanup
        for _, temp_file in active_processes:
            try: os.remove(temp_file)
            except: pass
            
        active_processes.clear()
        if campaign_state["status"] != "stopped":
            campaign_state["status"] = "finished"
            campaign_state["logs"].append("🏁 Campanha finalizada.")

    except Exception as e:
        campaign_state["status"] = "idle"
        campaign_state["logs"].append(f"❌ Erro no orquestrador: {str(e)}")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5005, debug=True)
