import http.server
import socketserver
import json
import os
import time
import threading
import random
from datetime import datetime

PORT = int(os.environ.get("PORT", 8000))
DB_FILE = "database.json"

# Base de dados estruturada localmente (Sem n8n / Make)
def create_empty_db():
    return {
        "metrics": {
            "leads": 0,
            "vendas": 0,
            "receita": 0.0,
            "conteudos": 0
        },
        "leads_db": [],
        "orders_db": [],
        "content_db": [],
        "feedback_db": [],
        "logs": []
    }

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    db = create_empty_db()
    save_db(db)
    return db

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log_event(db, agente, tarefa, evento, status="Sucesso"):
    log_entry = {
        "hora": datetime.now().strftime("%H:%M:%S"),
        "agente": agente,
        "tarefa": tarefa,
        "evento": evento,
        "status": status
    }
    db["logs"].insert(0, log_entry)
    db["logs"] = db["logs"][:20]

# --- MOTOR AUTÓNOMO DOS AGENTES DE IA ---
def run_autonomous_agents():
    """
    Simula e executa autonomamente as rotinas dos 6 Agentes (Research, Content,
    Funnel, Sales, Product, Analytics) com base nas regras do projeto.
    """
    hooks = [
        "Estás a usar IA como chatbot? Faz isto.",
        "A diferença entre um prompt e um workflow.",
        "3 tarefas que eu automatizaria primeiro.",
        "O erro nº1 em automações com IA.",
        "Como transformar feedback em produto."
    ]

    while True:
        time.sleep(15) # Executa ciclo autónomo periodicamente
        db = load_db()

        # Seleção de agente para simular execução autónoma de pipeline
        agente_choice = random.choice(["Research", "Content", "Funnel", "Analytics"])

        if agente_choice == "Research":
            log_event(db, "Research Agent", "Análise de Mercado", "Nova oportunidade mapeada: Templates de IA para PMEs")
        elif agente_choice == "Content":
            hook = random.choice(hooks)
            db["metrics"]["conteudos"] += 1
            db["content_db"].append({"hook": hook, "status": "draft", "created_at": datetime.now().isoformat()})
            log_event(db, "Content Agent", "Geração de Copy", f"Novo rascunho gerado: '{hook}'")
        elif agente_choice == "Funnel":
            log_event(db, "Funnel Agent", "Otimização de Conversão", "Verificação da sequência de e-mails concluída")
        elif agente_choice == "Analytics":
            log_event(db, "Analytics Agent", "Auditoria de KPIs", f"Métricas atualizadas: {db['metrics']['vendas']} vendas e €{db['metrics']['receita']:.2f} acumulados")

        save_db(db)

# Iniciar agente em thread paralela
threading.Thread(target=run_autonomous_agents, daemon=True).start()


class EngineHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        db = load_db()

        try:
            payload = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            payload = {}

        # 1. Endpoint POST /lead (Captura de Leads e Regras de Email)
        if self.path == '/lead' or self.path == '/api/lead':
            email = payload.get('email', '').strip().lower()
            consent = payload.get('consent', True)

            if not email:
                self.send_error(400, "E-mail e obrigatorio")
                return

            if consent:
                db["metrics"]["leads"] += 1
                lead_data = {
                    "email": email,
                    "first_name": payload.get('first_name', ''),
                    "source": payload.get('source', 'organico'),
                    "tags": ["lead"], # TAG lead -> sequencia de educacao
                    "created_at": datetime.now().isoformat()
                }
                db["leads_db"].append(lead_data)
                log_event(db, "Funnel Agent", "Captura de Lead", f"Novo Lead Registado: {email} (Tag: lead)")
                save_db(db)

                self._send_json({"ok": True, "next_action": "send_lead_magnet", "tags": lead_data["tags"]})
            else:
                self._send_json({"ok": False, "reason": "Consentimento nao concedido"}, status=400)

        # 2. Endpoint POST /purchase (Processamento de Compras / Reembolsos / Retenção de Fundos)
        elif self.path == '/purchase' or self.path == '/api/purchase':
            event_type = payload.get('event', 'purchase')
            order_id = payload.get('order_id', f"ORD-{int(time.time())}")
            email = payload.get('email', '').strip().lower()
            amount = float(payload.get('amount', 29.0)) # Valor padrao €29

            if event_type == 'purchase':
                db["metrics"]["vendas"] += 1
                db["metrics"]["receita"] += amount
                
                # Regra: IF customer=true THEN stop sales_sequence AND start onboarding / add tag customer
                order_entry = {
                    "order_id": order_id,
                    "email": email,
                    "amount": amount,
                    "currency": payload.get('currency', 'EUR'),
                    "status": "paid",
                    "tags": ["customer"],
                    "timestamp": datetime.now().isoformat()
                }
                db["orders_db"].append(order_entry)
                log_event(db, "Sales/Support Agent", "Processar Pagamento", f"COMPRA CONFIRMADA: +€{amount:.2f} ({email}) - Tag: customer")
                
            elif event_type == 'refund':
                db["metrics"]["receita"] -= amount
                # Regra: IF refund=true THEN stop upsell AND create support_task
                log_event(db, "Sales/Support Agent", "Processar Reembolso", f"REEMBOLSO PROCESSADO: -€{amount:.2f} ({email}) - Suporte Notificado")

            save_db(db)
            self._send_json({"ok": True, "event": event_type, "saldo_retido": db["metrics"]["receita"]})

        # 3. Endpoint POST /content-approved
        elif self.path == '/content-approved':
            content_id = payload.get('content_id')
            status = payload.get('status', 'approved')
            log_event(db, "Content Agent", "Aprovação de Conteúdo", f"Conteúdo #{content_id} alterado para {status}")
            save_db(db)
            self._send_json({"ok": True, "status": status})

        # 4. Endpoint POST /feedback
        elif self.path == '/feedback':
            msg = payload.get('message', '')
            db["feedback_db"].append({"message": msg, "rating": payload.get('rating', 5)})
            log_event(db, "Product Agent", "Feedback Miner", "Novo feedback de cliente guardado")
            save_db(db)
            self._send_json({"ok": True})

        else:
            self.send_error(404, "Endpoint nao encontrado")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


load_db()

print(f"\n⚡ AI INCOME ENGINE V2 (AUTÓNOMO & LOCAL) ATIVO!")
print(f"🖥️ Cyber HQ Dashboard ativo na porta {PORT}")
print(f"📥 Endpoint Lead: /lead")
print(f"💳 Endpoint Purchase: /purchase\n")

socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("0.0.0.0", PORT), EngineHandler) as httpd:
    httpd.serve_forever()
