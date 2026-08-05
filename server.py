import http.server
import socketserver
import json
import os
import time
import threading
import random
from datetime import datetime

print("--- DIAGNÓSTICO DE ARRANQUE ---")
print("ENV MONGO_URI presente?:", bool(os.environ.get("MONGO_URI")))
print("ENV GEMINI_API_KEY presente?:", bool(os.environ.get("GEMINI_API_KEY")))

# Importações de bibliotecas externas com tratamento de segurança
try:
    from pymongo import MongoClient
    print("Biblioteca pymongo importada com sucesso!")
except Exception as e:
    MongoClient = None
    print("❌ ERRO AO IMPORTAR PYMONGO:", e)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("Biblioteca google-generativeai importada com sucesso!")
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai em falta no ambiente.")

try:
    from imagekitio import ImageKit
except ImportError:
    ImageKit = None

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    cloudinary = None

try:
    import stripe
except ImportError:
    stripe = None

PORT = int(os.environ.get("PORT", 8000))
DB_FILE = "database.json"

# ==========================================
# CONFIGURAÇÕES DE VARIÁVEIS DE AMBIENTE
# ==========================================
MONGO_URI = os.environ.get("MONGO_URI")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
N8N_LEAD_WEBHOOK_URL = os.environ.get("N8N_LEAD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configurar o Gemini AI (Plano Gratuito)
gemini_model = None
if GEMINI_API_KEY and GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        print("✅ Gemini AI conectado com sucesso!")
    except Exception as e:
        print("❌ Erro ao configurar Gemini AI:", e)

# ImageKit Config
imagekit_client = None
if ImageKit:
    try:
        imagekit_client = ImageKit()
        print("Connected to ImageKit successfully!")
    except Exception as e:
        print("❌ ImageKit Initialization Error:", e)

# Cloudinary Config
CLOUDINARY_CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD and cloudinary:
    try:
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD,
            api_key=CLOUDINARY_KEY,
            api_secret=CLOUDINARY_SECRET
        )
        print("Connected to Cloudinary successfully!")
    except Exception as e:
        print("❌ Cloudinary Initialization Error:", e)

# Inicialização MongoDB com Diagnóstico Detalhado
db_mongo = None
if MONGO_URI and MongoClient:
    try:
        print("A tentar ligar ao MongoDB Atlas...")
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        mongo_client.admin.command('ping')
        db_mongo = mongo_client["motor_de_renda"]
        print("✅ CONECTADO AO MONGODB ATLAS COM SUCESSO!")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NA LIGAÇÃO AO MONGODB: {e}")
else:
    print("⚠️ Condição do MongoDB ignorada: MONGO_URI ou MongoClient estão em falta.")

# Inicialização Stripe
if STRIPE_SECRET_KEY and stripe:
    stripe.api_key = STRIPE_SECRET_KEY


def estado_inicial():
    return {
        "metrics": {
            "leads": 2,
            "vendas": 1,
            "receita": 29.0,
            "conteudos": 2
        },
        "test_metrics": {
            "leads": 0,
            "vendas": 0,
            "receita": 0.0
        },
        "leads_db": [{"email": "exemplo@lead.com", "created_at": datetime.now().isoformat()}],
        "orders_db": [{"email": "cliente@stripe.com", "amount": 29.0, "timestamp": datetime.now().isoformat()}],
        "content_db": [
            {
                "id": "content_init_1",
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "Content Agent",
                "tipo": "E-Book / Livro",
                "titulo": "Manual Prático de Automação com IA (PDF)",
                "conteudo": "Livro digital de 45 páginas gerado com estratégias de workflows.",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "content_init_2",
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "Content Agent",
                "tipo": "Vídeo / VSL",
                "titulo": "Vídeo de Vendas: Como Escalar com Agentes IA",
                "conteudo": "Roteiro e animação renderizada para anúncios de alta conversão.",
                "created_at": datetime.now().isoformat()
            }
        ],
        "memoria_temas": [],
        "feedback_db": [],
        "logs": [
            {
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "System",
                "tarefa": "Inicialização",
                "evento": "Motor V3 carregado com persistência em nuvem e Gemini IA.",
                "status": "Sucesso",
                "is_test": False
            }
        ],
        "test_logs": []
    }


def carregar_db():
    base = estado_inicial()
    data = None
    
    if db_mongo is not None:
        try:
            doc = db_mongo["app_state"].find_one({"_id": "global_state"})
            if doc:
                doc.pop("_id", None)
                data = doc
                print("📦 Dados carregados com sucesso do MongoDB Atlas!")
        except Exception as e:
            print("❌ Erro ao ler do MongoDB:", e)

    if not data:
        for filename in [DB_FILE, "banco de dados.json"]:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        print("📦 Dados carregados do ficheiro JSON local.")
                        break
                except Exception:
                    pass
        
    if data:
        for key, val in base.items():
            if key not in data or not data[key]:
                data[key] = val
        return data
        
    return base


def guardar_db():
    if db_mongo is not None:
        try:
            db_mongo["app_state"].replace_one(
                {"_id": "global_state"},
                DB,
                upsert=True
            )
        except Exception as e:
            print("❌ Erro ao escrever no MongoDB:", e)

    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("❌ Erro ao guardar BD local:", e)


DB = carregar_db()


def log_event(agente, tarefa, evento, status="Sucesso", is_test=False):
    log_entry = {
        "hora": datetime.now().strftime("%H:%M:%S"),
        "agente": agente,
        "tarefa": tarefa,
        "evento": evento,
        "status": status,
        "is_test": is_test
    }
    
    if is_test:
        DB.setdefault("test_logs", []).insert(0, log_entry)
        DB["test_logs"] = DB["test_logs"][:15]
    else:
        DB.setdefault("logs", []).insert(0, log_entry)
        DB["logs"] = DB["logs"][:20]
    
    guardar_db()


def run_autonomous_agents():
    while True:
        try:
            time.sleep(20)
            agente_choice = random.choice(["Research", "Content", "Funnel", "Analytics"])

            if agente_choice == "Research":
                if gemini_model:
                    res = gemini_model.generate_content("Gera uma oportunidade de mercado curta e direta para infoprodutos de IA em português.")
                    texto = res.text.strip()
                else:
                    texto = "Nova oportunidade mapeada: Templates de IA para PMEs"
                log_event("Research Agent", "Análise de Mercado", texto)

            elif agente_choice == "Content":
                if gemini_model:
                    res = gemini_model.generate_content("Cria um título e um breve resumo (1 parágrafo) em português para um infoproduto digital de automação com IA.")
                    texto_ia = res.text.strip()
                else:
                    texto_ia = "Manual Prático de Automação com IA gerado por simulação."
                
                DB["metrics"]["conteudos"] = DB.get("metrics", {}).get("conteudos", 0) + 1
                
                content_item = {
                    "id": f"content_{int(time.time() * 1000)}",
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "agente": "Content Agent",
                    "tipo": "E-Book / IA Gemini",
                    "titulo": "Gerado por IA (Gemini)",
                    "conteudo": texto_ia,
                    "created_at": datetime.now().isoformat()
                }
                
                DB.setdefault("content_db", []).insert(0, content_item)
                DB["content_db"] = DB["content_db"][:30]
                guardar_db()
                log_event("Content Agent", "Criação de Conteúdo", f"Gerado por IA: {texto_ia[:60]}...")

            elif agente_choice == "Funnel":
                log_event("Funnel Agent", "Otimização de Conversão", "IA verificou o fluxo de leads e otimizou os funis de conversão.")

            elif agente_choice == "Analytics":
                log_event("Analytics Agent", "Auditoria de KPIs", f"Métricas auditadas: {DB['metrics']['vendas']} vendas e €{DB['metrics']['receita']:.2f} acumulados.")

        except Exception as e:
            print("Erro na thread autónoma:", e)


# Iniciar motor de agentes autónomos em background
threading.Thread(target=run_autonomous_agents, daemon=True).start()


class EngineHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/data':
            response_data = DB.copy()
            response_data["contents"] = DB.get("content_db", [])
            response_data["memoria_temas"] = DB.get("memoria_temas", [])
            self._send_json(response_data)
        elif self.path == '/meta.json':
            self._send_json({"name": "Cyber Office", "version": "3.0", "status": "online"})
        elif self.path == '/api/reset-tests':
            DB["test_metrics"] = {"leads": 0, "vendas": 0, "receita": 0.0}
            DB["test_logs"] = []
            guardar_db()
            self._send_json({"ok": True, "message": "Testes limpos com sucesso via GET!"})
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            payload = {}

        is_test = payload.get('is_test', True)

        if self.path == '/webhook/stripe':
            event_type = payload.get('type')
            if event_type == 'checkout.session.completed':
                session = payload.get('data', {}).get('object', {})
                email = session.get('customer_email') or session.get('customer_details', {}).get('email', 'cliente@stripe.com')
                amount_total = session.get('amount_total', 2900) / 100.0
                
                DB["metrics"]["vendas"] += 1
                DB["metrics"]["receita"] += amount_total
                DB["orders_db"].append({"email": email, "amount": amount_total, "timestamp": datetime.now().isoformat()})
                guardar_db()
                
                log_event("Sales Agent", "Pagamento Stripe", f"COMPRA REAL: +€{amount_total:.2f} ({email})", is_test=False)
                self._send_json({"received": True})
            else:
                self._send_json({"received": True, "note": "Evento ignorado"})

        elif self.path == '/api/purge-content':
            content_id = payload.get("content_id")
            imagekit_file_id = payload.get("imagekit_file_id")
            cloudinary_public_id = payload.get("cloudinary_public_id")
            tema = payload.get("tema")

            if imagekit_file_id and imagekit_client:
                try:
                    imagekit_client.delete_file(imagekit_file_id)
                except Exception as e:
                    print("Erro ImageKit Purge:", e)

            if cloudinary_public_id and cloudinary:
                try:
                    cloudinary.uploader.destroy(cloudinary_public_id)
                except Exception as e:
                    print("Erro Cloudinary Purge:", e)

            if tema:
                DB.setdefault("memoria_temas", []).append({
                    "tema": tema,
                    "postado_em": datetime.now().isoformat()
                })
                DB["memoria_temas"] = DB["memoria_temas"][-200:]

            if content_id and "content_db" in DB:
                DB["content_db"] = [item for item in DB["content_db"] if item.get("id") != content_id]

            guardar_db()
            log_event("System", "Auto-Purge", f"Conteúdo {content_id or tema} limpo com sucesso!")
            self._send_json({"ok": True, "message": "Conteúdo e ficheiros limpos com sucesso!"})

        elif self.path in ['/lead', '/api/lead']:
            email = payload.get('email', 'teste@lead.com').strip().lower()
            first_name = payload.get('first_name', 'Lead')
            source = payload.get('source', 'dashboard_sandbox')
            consent = payload.get('consent', True)

            if is_test:
                DB.setdefault("test_metrics", {"leads": 0, "vendas": 0, "receita": 0.0})
                DB["test_metrics"]["leads"] += 1
                guardar_db()
                log_event("Funnel Agent", "Simulação Lead", f"TESTE: Lead registado ({email})", is_test=True)
            else:
                DB["metrics"]["leads"] += 1
                DB["leads_db"].append({"email": email, "created_at": datetime.now().isoformat()})
                guardar_db()
                log_event("Funnel Agent", "Captura de Lead", f"Novo Lead Registado: {email}", is_test=False)

            if N8N_LEAD_WEBHOOK_URL:
                try:
                    import urllib.request
                    req_data = json.dumps({
                        "email": email,
                        "first_name": first_name,
                        "source": source,
                        "consent": consent
                    }).encode('utf-8')
                    req = urllib.request.Request(N8N_LEAD_WEBHOOK_URL, data=req_data, headers={'Content-Type': 'application/json'})
                    urllib.request.urlopen(req, timeout=5)
                except Exception as e:
                    print(f"Erro ao disparar webhook para n8n: {e}")

            self._send_json({"ok": True, "message": f"Lead {'[TESTE]' if is_test else '[REAL]'} guardada com sucesso!"})

        elif self.path in ['/purchase', '/api/purchase']:
            email = payload.get('email', 'teste@venda.com').strip().lower()
            amount = float(payload.get('amount', 29.0))

            if is_test:
                DB.setdefault("test_metrics", {"leads": 0, "vendas": 0, "receita": 0.0})
                DB["test_metrics"]["vendas"] += 1
                DB["test_metrics"]["receita"] += amount
                guardar_db()
                log_event("Sales Agent", "Simulação Venda", f"TESTE: +€{amount:.2f} ({email})", is_test=True)
            else:
                DB["metrics"]["vendas"] += 1
                DB["metrics"]["receita"] += amount
                DB["orders_db"].append({"email": email, "amount": amount, "timestamp": datetime.now().isoformat()})
                guardar_db()
                log_event("Sales Agent", "Processar Pagamento", f"COMPRA REAL: +€{amount:.2f} ({email})", is_test=False)

            self._send_json({"ok": True, "message": f"Venda {'[TESTE]' if is_test else '[REAL]'} de €{amount:.2f} processada!"})

        elif self.path in ['/feedback', '/api/feedback']:
            comentario = payload.get('comentario', '').strip()
            if comentario:
                DB.setdefault("feedback_db", []).insert(0, {
                    "comentario": comentario,
                    "timestamp": datetime.now().isoformat()
                })
                guardar_db()
                log_event("Analytics Agent", "Feedback Recebido", "Novo comentário registado")
            self._send_json({"ok": True, "message": "Feedback registado com sucesso!"})

        elif self.path == '/api/reset-tests':
            DB["test_metrics"] = {"leads": 0, "vendas": 0, "receita": 0.0}
            DB["test_logs"] = []
            guardar_db()
            self._send_json({"ok": True, "message": "Testes limpos com sucesso via POST!"})

        else:
            self._send_json({"ok": False, "reason": "Endpoint nao encontrado"}, status=404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("0.0.0.0", PORT), EngineHandler) as httpd:
    print(f"Servidor a rodar na porta {PORT}...")
    httpd.serve_forever()
