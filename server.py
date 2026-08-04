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

def create_empty_db():
    return {
        "metrics": {
            "leads": 0,
            "vendas": 0,
            "receita": 0.0,
            "conteudos": 0
        },
        "test_metrics": {
            "leads": 0,
            "vendas": 0,
            "receita": 0.0
        },
        "leads_db": [],
        "orders_db": [],
        "content_db": [],
        "feedback_db": [],
        "logs": [],
        "test_logs": []
    }

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
                if "test_metrics" not in db:
                    db["test_metrics"] = {"leads": 0, "vendas": 0, "receita": 0.0}
                if "test_logs" not in db:
                    db["test_logs"] = []
                return db
        except Exception:
            pass
    db = create_empty_db()
    save_db(db)
    return db

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log_event(db, agente, tarefa, evento, status="Sucesso", is_test=False):
    log_entry = {
        "hora": datetime.now().strftime("%H:%M:%S"),
        "agente": agente,
        "tarefa": tarefa,
        "evento": evento,
        "status": status,
        "is_test": is_test
    }
    
    if is_test:
        db["test_logs"].insert(0, log_entry)
        db["test_logs"] = db["test_logs"][:15]
    else:
        db["logs"].insert(0, log_entry)
        db["logs"] = db["logs"][:20]

def run_autonomous_agents():
    hooks = [
        "Estás a usar IA como chatbot? Faz isto.",
        "A diferença entre um prompt e um workflow.",
        "3 tarefas que eu automatizaria primeiro.",
        "O erro nº1 em automações com IA.",
        "Como transformar feedback em produto."
    ]

    while True:
        time.sleep(15)
        db = load_db()
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
            self._send_json(load_db())
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

        is_test = payload.get('is_test', False)

        if self.path == '/lead' or self.path == '/api/lead':
            email = payload.get('email', '').strip().lower()
            consent = payload.get('consent', True)

            if not email:
                self._send_json({"ok": False, "reason": "E-mail obrigatorio"}, status=400)
                return

            if is_test:
                db["test_metrics"]["leads"] += 1
                log_event(db, "Funnel Agent", "Simulação Lead", f"TESTE: Lead registado ({email})", is_test=True)
            else:
                db["metrics"]["leads"] += 1
                lead_data = {
                    "email": email,
                    "first_name": payload.get('first_name', ''),
                    "source": payload.get('source', 'organico'),
                    "tags": ["lead"],
                    "created_at": datetime.now().isoformat()
                }
                db["leads_db"].append(lead_data)
                log_event(db, "Funnel Agent", "Captura de Lead", f"Novo Lead Registado: {email} (Tag: lead)", is_test=False)

            save_db(db)
            self._send_json({"ok": True, "message": f"Lead {'[TESTE]' if is_test else '[REAL]'} registado com sucesso!"})

        elif self.path == '/purchase' or self.path == '/api/purchase':
            event_type = payload.get('event', 'purchase')
            email = payload.get('email', '').strip().lower()
            amount = float(payload.get('amount', 29.0))

            if is_test:
                db["test_metrics"]["vendas"] += 1
                db["test_metrics"]["receita"] += amount
                log_event(db, "Sales Agent", "Simulação Venda", f"TESTE: +€{amount:.2f} ({email})", is_test=True)
            else:
                db["metrics"]["vendas"] += 1
                db["metrics"]["receita"] += amount
                order_entry = {
                    "order_id": f"ORD-{int(time.time())}",
                    "email": email,
                    "amount": amount,
                    "currency": "EUR",
                    "status": "paid",
                    "tags": ["customer"],
                    "timestamp": datetime.now().isoformat()
                }
                db["orders_db"].append(order_entry)
                log_event(db, "Sales Agent", "Processar Pagamento", f"COMPRA REAL: +€{amount:.2f} ({email})", is_test=False)

            save_db(db)
            self._send_json({"ok": True, "message": f"Venda {'[TESTE]' if is_test else '[REAL]'} de €{amount:.2f} processada!"})

        elif self.path == '/api/reset-tests':
            db["test_metrics"] = {"leads": 0, "vendas": 0, "receita": 0.0}
            db["test_logs"] = []
            save_db(db)
            self._send_json({"ok": True, "message": "Métricas de teste reiniciadas!"})

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

load_db()

socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("0.0.0.0", PORT), EngineHandler) as httpd:
    httpd.serve_forever()
