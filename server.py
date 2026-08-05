import http.server
import socketserver
import json
import os
import time
import threading
import random
from datetime import datetime

print("--- DIAGNÓSTICO DE ARRANQUE V4 ---")
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
                "tipo": "Manual / E-book Técnico",
                "titulo": "Manual Definitivo: Como Criar Agentes de IA e Arquiteturas Autónomas em Python",
                "conteudo": "## 1. Visão Geral e Fundamentos Teóricos\n\nEste manual técnico foi desenhado para servir como referência completa. Nele abordamos a construção de sistemas autónomos de inteligência artificial de nível corporativo utilizando Python.\n\n### 1.1 Arquitetura de Agentes ReAct\nA arquitetura Reasoning and Acting (ReAct) permite que o modelo alterne entre passos de raciocínio lógico e chamadas a ferramentas externas. Abaixo encontra-se a estrutura básica de inicialização:\n\n```python\nimport os\nfrom openai import OpenAI\n\nclient = OpenAI(\n    base_url=\"[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)\",\n    api_key=os.environ.get(\"GROQ_API_KEY\")\n)\n\nresponse = client.chat.completions.create(\n    model=\"llama-3.1-8b-instant\",\n    messages=[{\"role\": \"user\", \"content\": \"Inicializar motor autónomo.\"}]\n)\nprint(response.choices[0].message.content)\n```\n\n## 2. Implementação de Ciclos Autónomos\n\nPara garantir que o sistema evolui de forma contínua, implementamos threads de background que geram novos módulos pedagógicos em formato de e-book e os sincronizam diretamente com a base de dados em tempo real.",
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
                "evento": "Motor V4 carregado com suporte a e-books profundos e API de auto-modificação de páginas HTML.",
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


def call_groq(messages_list, fallback_text):
    if not groq_client:
        return fallback_text
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_list,
            temperature=0.7,
            max_tokens=4096
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("Erro na chamada à Groq:", e)
        return fallback_text


def run_autonomous_agents():
    while True:
        try:
            time.sleep(120)  # Ciclo a cada 2 minutos para garantir geração profunda
            print("📚 [ECOSSISTEMA AUTÓNOMO] A IA está a compilar um novo E-book Técnico completo...")

            research_messages = [
                {
                    "role": "system", 
                    "content": "És um Arquiteto de Software e Autor técnico sênior."
                },
                {
                    "role": "user", 
                    "content": "Define um tema técnico avançado e altamente específico para um e-book de programação e engenharia de IA (ex: 'Arquitetura de Sistemas Multi-Agente com LangChain e Python', 'Desenvolvimento de Pipelines de Processamento de Dados em Tempo Real com Webhooks e Redis', 'Engenharia de Prompts Avançada e Fine-Tuning de LLMs Open Source')."
                }
            ]
            research_text = call_groq(research_messages, "Arquitetura Avançada de Sistemas Multi-Agente em Python")
            log_event("Research Agent", "Pesquisa de E-book", research_text)

            content_messages = [
                {
                    "role": "system", 
                    "content": (
                        "És um escritor técnico de elite, autor de best-sellers de programação e professor universitário. "
                        "Escreve um MÓDULO PEDAGÓGICO / E-BOOK EXTREMAMENTE LONGO, denso, estruturado e profissional (equivalente a dezenas de páginas de um livro físico). "
                        "O conteúdo DEVE conter múltiplos capítulos detalhados (ex: 1. Introdução Teórica, 2. Arquitetura de Componentes, 3. Implementação Prática com Código Completo, 4. Casos de Uso Empresariais, 5. Exercícios de Fixação). "
                        "ATENÇÃO CRÍTICA: O campo 'conteudo' DEVE ser estritamente uma STRING gigante formatada em Markdown puro (usando ##, ###, listas detalhadas e blocos de código ```python). NUNCA devolvas um objeto JSON ou dicionário aninhado dentro do conteúdo. "
                        "Responde estritamente em formato JSON puro com exatamente duas chaves: 'titulo' (string) e 'conteudo' (string gigante em Markdown). "
                        "NÃO incluas blocos ```json extras à volta da resposta."
                    )
                },
                {
                    "role": "user", 
                    "content": f"Escreve o manual/e-book completo, exaustivo e aprofundado sobre: '{research_text}'. Garante que o texto é rico, longo, repleto de código prático e explicações profundas."
                }
            ]
            raw_ai_response = call_groq(content_messages, '{"titulo": "Manual Avançado", "conteudo": "## Capítulo 1\\n\\nConteúdo em expansão..."}')
            
            try:
                if "```json" in raw_ai_response:
                    raw_ai_response = raw_ai_response.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_ai_response:
                    raw_ai_response = raw_ai_response.split("```")[1].split("```")[0].strip()
                
                parsed_data = json.loads(raw_ai_response)
                final_titulo = parsed_data.get("titulo", f"Manual Prático: {research_text}")
                final_conteudo = parsed_data.get("conteudo", "Conteúdo técnico em processamento...")
                
                # Blindagem absoluta contra dicionários ou listas no conteúdo
                if isinstance(final_conteudo, dict):
                    blocos = []
                    for k, v in final_conteudo.items():
                        blocos.append(f"## {k}\n\n" + (str(v) if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False, indent=2)))
                    final_conteudo = "\n\n".join(blocos)
                elif isinstance(final_conteudo, list):
                    final_conteudo = "\n\n".join([str(item) for item in final_conteudo])
                elif not isinstance(final_conteudo, str):
                    final_conteudo = str(final_conteudo)

            except Exception as e:
                print("Erro ao parsear JSON do e-book:", e)
                final_titulo = f"Manual Completo: {research_text}"
                final_conteudo = f"## 1. Introdução a {research_text}\n\nNeste capítulo aprofundado, exploramos os conceitos fundamentais e arquiteturais necessários para dominar esta tecnologia.\n\n### 1.1 Fundamentos e Contexto\nA engenharia de software moderna exige padrões robustos de implementação...\n\n### 1.2 Implementação Prática em Python\nAbaixo encontra-se a referência completa de código:\n```python\n# Arquitetura de referência\ndef executar_pipeline():\n    print('Executando módulo autónomo...')\n\nif __name__ == '__main__':\n    executar_pipeline()\n```"

            DB["metrics"]["conteudos"] = DB.get("metrics", {}).get("conteudos", 0) + 1
            content_item = {
                "id": f"content_{int(time.time() * 1000)}",
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "Content Agent (E-book Engine)",
                "tipo": "Manual / E-book Técnico",
                "titulo": final_titulo,
                "conteudo": final_conteudo,
                "created_at": datetime.now().isoformat()
            }
            
            DB.setdefault("content_db", []).insert(0, content_item)
            DB["content_db"] = DB["content_db"][:200]
            log_event("Content Agent", "Portal Atualizado", f"E-book publicado: {final_titulo}")
            guardar_db()

        except Exception as e:
            print("Erro no ciclo autónomo de e-books:", e)


threading.Thread(target=run_autonomous_agents, daemon=True).start()


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
            self._send_json({"name": "Cyber Office", "version": "4.0", "status": "online"})
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

        # Endpoint para a IA ler o código HTML das páginas (Portal ou Landing)
        if self.path == '/api/read-page':
            page_name = payload.get('page', 'landing.html').strip().lower()
            filename = 'portal.html' if 'portal' in page_name else 'landing.html'
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._send_json({"ok": True, "page": filename, "content": content})
            else:
                self._send_json({"ok": False, "reason": f"Ficheiro {filename} não encontrado no servidor."})

        # Endpoint para a IA atualizar/modificar diretamente o design e código HTML das páginas
        elif self.path == '/api/update-page':
            page_name = payload.get('page', 'landing.html').strip().lower()
            html_content = payload.get('html_content', '')
            filename = 'portal.html' if 'portal' in page_name else 'landing.html'
            
            if html_content:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                log_event("Design Agent", "Modificação de Página", f"A IA atualizou com sucesso o código da página {filename}.")
                guardar_db()
                self._send_json({"ok": True, "message": f"Página {filename} atualizada e aplicada com sucesso!"})
            else:
                self._send_json({"ok": False, "reason": "O conteúdo HTML fornecido está vazio."})

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
