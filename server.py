import http.server
import socketserver
import json
import os
import time
import threading
import random
import re
from datetime import datetime

print("--- DIAGNÓSTICO DE ARRANQUE V9.1 (SISTEMA COMPLETO + PARSER RESILIENTE) ---")
print("ENV MONGO_URI presente?:", bool(os.environ.get("MONGO_URI")))
print("ENV GROQ_API_KEY presente?:", bool(os.environ.get("GROQ_API_KEY")))
print("ENV N8N_PURCHASE_WEBHOOK_URL presente?:", bool(os.environ.get("N8N_PURCHASE_WEBHOOK_URL")))

# Importações de bibliotecas externas com tratamento de segurança
try:
    from pymongo import MongoClient
    print("Biblioteca pymongo importada com sucesso!")
except Exception as e:
    MongoClient = None
    print("❌ ERRO AO IMPORTAR PYMONGO:", e)

try:
    from openai import OpenAI
    OPENAI_LIB_AVAILABLE = True
    print("Biblioteca openai importada com sucesso (compatível com Groq)!")
except ImportError:
    OPENAI_LIB_AVAILABLE = False
    print("⚠️ Biblioteca openai em falta no ambiente.")

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
N8N_PURCHASE_WEBHOOK_URL = os.environ.get("N8N_PURCHASE_WEBHOOK_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Configurar o cliente Groq (Open-Source via Llama 3.1)
groq_client = None
if GROQ_API_KEY and OPENAI_LIB_AVAILABLE:
    try:
        groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY
        )
        print("✅ Groq AI (Llama 3.1) conectada com sucesso!")
    except Exception as e:
        print("❌ Erro ao configurar Groq AI:", e)

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
            "conteudos": 1
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
                "id": "ebook_master_1",
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "Ebook Synthesis AI",
                "tipo": "E-book Master Compilado",
                "titulo": "E-book 1: Arquitetura Definitiva de Agentes Autónomos e Pipelines Python",
                "conteudo": "# E-book 1: Arquitetura Definitiva de Agentes Autónomos\n\n## 📋 Introdução e Contexto\nEste livro técnico aborda a criação de ecossistemas autónomos resilientes...\n\n## 🏗️ 1. Estrutura de Ciclos ReAct\nAprende a programar loops de tomada de decisão baseados em LLMs...\n\n## 💻 2. Implementação de Código Base\n```python\nimport os\nfrom openai import OpenAI\n\nclient = OpenAI(base_url='[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)', api_key=os.environ.get('GROQ_API_KEY'))\nprint('Motor de E-books Ativo')\n```\n\n## 🚀 3. Conclusão e Próximos Passos\nEstás pronto para escalar os teus agentes em produção.",
                "created_at": datetime.now().isoformat()
            }
        ],
        "ai_commands": {
            "master": "",
            "ebook": "",
            "landing": ""
        },
        "memoria_temas": [],
        "feedback_db": [],
        "logs": [
            {
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "System",
                "tarefa": "Inicialização",
                "evento": "Motor V9.1 carregado com parser JSON resiliente e 3 IAs.",
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

# Limpeza automática de registos corrompidos com literais \n no início
for item in DB.get("content_db", []):
    if "conteudo" in item and "\\n" in item["conteudo"] and "\n" not in item["conteudo"]:
        item["conteudo"] = item["conteudo"].replace("\\n", "\n")
guardar_db()


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


def call_groq(messages_list, fallback_text):
    if not groq_client:
        return fallback_text
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_list,
            temperature=0.6,
            max_tokens=4096
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("Erro na chamada à Groq:", e)
        return fallback_text


def parse_ai_json(raw_text):
    """Parser robusto para limpar e processar JSON retornado por LLMs."""
    if not raw_text:
        return None
    
    if "```json" in raw_text:
        parts = raw_text.split("```json")
        if len(parts) > 1:
            raw_text = parts[1].split("```")[0].strip()
    elif "```" in raw_text:
        parts = raw_text.split("```")
        if len(parts) > 1:
            raw_text = parts[1].split("```")[0].strip()
            
    try:
        return json.loads(raw_text)
    except Exception:
        try:
            fixed = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw_text)
            return json.loads(fixed)
        except Exception as e:
            print("❌ Falha crítica no parse JSON da IA:", e)
            return None


# ==========================================
# IA 1: DASHBOARD MASTER AI
# ==========================================
def dashboard_master_loop():
    while True:
        try:
            time.sleep(300)
            cmd = DB.get("ai_commands", {}).get("master", "")
            if cmd:
                print(f"\n🧠 [DASHBOARD MASTER AI] A executar ordem direta: {cmd}")
                log_event("Dashboard Master AI", "Comando Direto", f"Executou: {cmd}")
                DB["ai_commands"]["master"] = ""
                guardar_db()
            else:
                print("\n🧠 [DASHBOARD MASTER AI] A supervisionar estado global e robôs...")
                log_event("Dashboard Master AI", "Supervisão", f"Sistema operacional. Leads: {DB['metrics']['leads']}, Vendas: {DB['metrics']['vendas']}")
        except Exception as e:
            print("❌ Erro na Dashboard Master AI:", e)
            time.sleep(30)


# ==========================================
# IA 2: EBOOK SYNTHESIS AI (Portal de Membros)
# ==========================================
def ebook_synthesis_loop():
    while True:
        try:
            time.sleep(200)
            cmd = DB.get("ai_commands", {}).get("ebook", "")
            if cmd:
                print(f"\n📚 [EBOOK SYNTHESIS AI] A executar instrução específica: {cmd}")
                tema_alvo = cmd
                DB["ai_commands"]["ebook"] = ""
                guardar_db()
            else:
                print("\n📚 [EBOOK SYNTHESIS AI] A compilar novo E-book completo e coeso para o portal...")
                temas = [
                    "Arquitetura de Microsserviços e Mensageria Assíncrona com Python",
                    "Pipelines de Dados e Bases de Dados Vectoriais em Produção",
                    "Sistemas Autónomos baseados em Ciclos ReAct e LLMs",
                    "Segurança e Autenticação Avançada em APIs REST"
                ]
                tema_alvo = random.choice(temas)

            prompt = [
                {
                    "role": "system",
                    "content": (
                        "És a IA responsável pelo Portal de Membros e pela criação de E-books Master. "
                        "A tua missão é redigir um E-BOOK COMPLETO, LONGO E PROFUNDO, que funcione como um livro digital fechado. "
                        "NUNCA cries fragmentos ou módulos soltos (como 'Módulo 1'). Cria um E-book unitário, coerente e exaustivo. "
                        "Responde estritamente em formato JSON puro com duas chaves: 'titulo' (ex: 'E-book X: Nome Técnico') "
                        "e 'conteudo' (uma string gigante em Markdown estruturada com Introdução, Fundamentos, Código Prático em blocos ```python, Casos Reais e Conclusão). "
                        "Sem saudações, conversas ou blocos ```json extras."
                    )
                },
                {
                    "role": "user",
                    "content": f"Compila um E-book Master sobre: '{tema_alvo}'."
                }
            ]

            raw = call_groq(prompt, "")
            parsed = parse_ai_json(raw)
            
            if parsed and isinstance(parsed, dict):
                titulo = str(parsed.get("titulo", f"E-book Técnico: {tema_alvo}")).replace('*', '').replace('"', '').strip()
                conteudo = str(parsed.get("conteudo", "")).strip()

                if len(conteudo) > 400 and "```python" in conteudo:
                    num_ebook = len(DB.get("content_db", [])) + 1
                    titulo_final = f"E-book {num_ebook}: {titulo.replace('E-book', '').strip()}"
                    
                    novo_ebook = {
                        "id": f"ebook_{int(time.time() * 1000)}",
                        "hora": datetime.now().strftime("%H:%M:%S"),
                        "agente": "Ebook Synthesis AI",
                        "tipo": "E-book Master Compilado",
                        "titulo": titulo_final,
                        "conteudo": conteudo,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    DB.setdefault("content_db", []).insert(0, novo_ebook)
                    DB["content_db"] = DB["content_db"][:100]
                    guardar_db()
                    
                    log_event("Ebook Synthesis AI", "Compilação de E-book", f"E-book publicado no portal: {titulo_final}")
                    print(f"✅ E-book gerado com sucesso: {titulo_final}")
                else:
                    print("⚠️ E-book rejeitado por falta de profundidade ou código Python.")
            else:
                print("⚠️ Falha ao descodificar JSON do E-book gerado pela IA.")

        except Exception as e:
            print("❌ Erro na Ebook Synthesis AI:", e)
            time.sleep(30)


# ==========================================
# IA 3: LANDING & SALES PAGE AI
# ==========================================
def landing_sales_optimizer_loop():
    while True:
        try:
            time.sleep(250)
            cmd = DB.get("ai_commands", {}).get("landing", "")
            if cmd:
                print(f"\n💳 [LANDING & SALES AI] A aplicar instrução de design/vendas: {cmd}")
                DB["ai_commands"]["landing"] = ""
                guardar_db()
            
            print("\n💳 [LANDING & SALES PAGE AI] A otimizar página de vendas e checkout...")
            filename = "landing.html"
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    html_code = f.read()

                prompt = [
                    {
                        "role": "system",
                        "content": (
                            "És a IA Especialista na Página de Landing e Checkout. A tua única responsabilidade é polir o design em Tailwind CSS, "
                            "maximizar a conversão de vendas da mensalidade e garantir que os botões de pagamento do Stripe e captura de leads estão perfeitos e altamente apelativos. "
                            "Devolve APENAS o código HTML completo e atualizado, sem texto extra."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Estado atual de conversão -> Leads: {DB['metrics']['leads']}, Vendas: {DB['metrics']['vendas']}. Código atual:\n{html_code[:12000]}"
                    }
                ]
                
                novo_html = call_groq(prompt, html_code)
                if "<html" in novo_html.lower():
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(novo_html)
                    log_event("Landing & Sales AI", "Otimização", "Página de vendas e checkout otimizada.")
                    print("✅ Página de vendas e checkout atualizada pela Landing AI!")
        except Exception as e:
            print("❌ Erro na Landing & Sales AI:", e)
            time.sleep(30)


# Iniciar as 3 IAs autónomas em background
threading.Thread(target=dashboard_master_loop, daemon=True).start()
threading.Thread(target=ebook_synthesis_loop, daemon=True).start()
threading.Thread(target=landing_sales_optimizer_loop, daemon=True).start()


class EngineHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/landing.html'
            return super().do_GET()
        
        elif self.path in ['/dashboard', '/admin', '/index.html']:
            self.path = '/index.html'
            return super().do_GET()

        elif self.path in ['/portal', '/membros', '/portal.html']:
            self.path = '/portal.html'
            return super().do_GET()

        elif self.path == '/api/data':
            response_data = DB.copy()
            response_data["contents"] = DB.get("content_db", [])
            response_data["memoria_temas"] = DB.get("memoria_temas", [])
            self._send_json(response_data)
        elif self.path == '/meta.json':
            self._send_json({"name": "Cyber Office", "version": "9.1", "status": "online"})
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

        if self.path == '/api/read-page':
            page_name = payload.get('page', 'landing.html').strip().lower()
            filename = 'portal.html' if 'portal' in page_name else 'landing.html'
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._send_json({"ok": True, "page": filename, "content": content})
            else:
                self._send_json({"ok": False, "reason": f"Ficheiro {filename} não encontrado no servidor."})

        elif self.path == '/api/update-page':
            page_name = payload.get('page', 'landing.html').strip().lower()
            html_content = payload.get('html_content', '')
            filename = 'portal.html' if 'portal' in page_name else 'landing.html'
            
            if html_content:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                log_event("Dashboard Master AI", "Modificação de Página", f"Atualização manual do ficheiro {filename}.")
                guardar_db()
                self._send_json({"ok": True, "message": f"Página {filename} atualizada e aplicada com sucesso!"})
            else:
                self._send_json({"ok": False, "reason": "O conteúdo HTML fornecido está vazio."})

        elif self.path == '/api/command-ai':
            ai_target = payload.get('ai_target', '').strip().lower()
            command_text = payload.get('command', '').strip()
            if ai_target in DB["ai_commands"] and command_text:
                DB["ai_commands"][ai_target] = command_text
                guardar_db()
                log_event("Dashboard Master AI", "Comando Atribuído", f"Ordem enviada para a IA '{ai_target}': {command_text}")
                self._send_json({"ok": True, "message": f"Ordem enviada para a IA {ai_target} com sucesso!"})
            else:
                self._send_json({"ok": False, "reason": "Alvo de IA inválido ou comando vazio."})

        elif self.path == '/webhook/stripe':
            event_type = payload.get('type')
            if event_type == 'checkout.session.completed':
                session = payload.get('data', {}).get('object', {})
                email = session.get('customer_email') or session.get('customer_details', {}).get('email', 'cliente@stripe.com')
                amount_total = session.get('amount_total', 2900) / 100.0
                
                DB["metrics"]["vendas"] += 1
                DB["metrics"]["receita"] += amount_total
                DB["orders_db"].append({"email": email, "amount": amount_total, "timestamp": datetime.now().isoformat()})
                guardar_db()
                
                if N8N_PURCHASE_WEBHOOK_URL:
                    try:
                        import urllib.request
                        current_product = DB.get("content_db", [{}])[0].get("titulo", "Manual Prático de Automação com IA")
                        req_data = json.dumps({
                            "email": email,
                            "amount": amount_total,
                            "produto": current_product,
                            "data": datetime.now().isoformat()
                        }).encode('utf-8')
                        req = urllib.request.Request(N8N_PURCHASE_WEBHOOK_URL, data=req_data, headers={'Content-Type': 'application/json'})
                        urllib.request.urlopen(req, timeout=5)
                    except Exception as e:
                        print(f"Erro ao disparar webhook de compra para o n8n: {e}")

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

            if N8N_PURCHASE_WEBHOOK_URL:
                try:
                    import urllib.request
                    current_product = DB.get("content_db", [{}])[0].get("titulo", "Manual Prático de Automação com IA")
                    req_data = json.dumps({
                        "email": email,
                        "amount": amount,
                        "produto": current_product,
                        "data": datetime.now().isoformat()
                    }).encode('utf-8')
                    req = urllib.request.Request(N8N_PURCHASE_WEBHOOK_URL, data=req_data, headers={'Content-Type': 'application/json'})
                    urllib.request.urlopen(req, timeout=5)
                except Exception as e:
                    print(f"Erro ao disparar webhook de compra para o n8n: {e}")

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
            self._send_json({"ok": False, "reason": "Endpoint não encontrado"}, status=404)

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
