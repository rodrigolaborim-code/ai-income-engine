import http.server
import socketserver
import json
import os
import time
import threading
import random
from datetime import datetime

PORT = int(os.environ.get("PORT", 8000))

DB = {
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
        DB["test_logs"].insert(0, log_entry)
        DB["test_logs"] = DB["test_logs"][:15]
    else:
        DB["logs"].insert(0, log_entry)
        DB["logs"] = DB["logs"][:20]

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
        agente_choice = random.choice(["Research", "Content", "Funnel", "Analytics"])

        if agente_choice == "Research":
            log_event("Research Agent", "Análise de Mercado", "Nova oportunidade mapeada: Templates de IA para PMEs")
        elif agente_choice == "Content":
            hook = random.choice(hooks)
            DB["metrics"]["conteudos"] += 1
            DB["content_db"].append({"hook": hook, "status": "draft", "created_at": datetime.now().isoformat()})
            log_event("Content Agent", "Geração de Copy", f"Novo rascunho gerado: '{hook}'")
        elif agente_choice == "Funnel":
            log_event("Funnel Agent", "Otimização de Conversão", "Verificação da sequência de e-mails concluída")
        elif agente_choice == "Analytics":
            log_event("Analytics Agent", "Auditoria de KPIs", f"Métricas atualizadas: {DB['metrics']['vendas']} vendas e €{DB['metrics']['receita']:.2f} acumulados")

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
            self._send_json(DB)
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

        if self.path in ['/lead', '/api/lead']:
            email = payload.get('email', 'teste@lead.com').strip().lower()

            if is_test:
                DB["test_metrics"]["leads"] += 1
                log_event("Funnel Agent", "Simulação Lead", f"TESTE: Lead registado ({email})", is_test=True)
            else:
                DB["metrics"]["leads"] += 1
                DB["leads_db"].append({"email": email, "created_at": datetime.now().isoformat()})
                log_event("Funnel Agent", "Captura de Lead", f"Novo Lead Registado: {email}", is_test=False)

            self._send_json({"ok": True, "message": f"Lead {'[TESTE]' if is_test else '[REAL]'} guardada com sucesso!"})

        elif self.path in ['/purchase', '/api/purchase']:
            email = payload.get('email', 'teste@venda.com').strip().lower()
            amount = float(payload.get('amount', 29.0))

            if is_test:
                DB["test_metrics"]["vendas"] += 1
                DB["test_metrics"]["receita"] += amount
                log_event("Sales Agent", "Simulação Venda", f"TESTE: +€{amount:.2f} ({email})", is_test=True)
            else:
                DB["metrics"]["vendas"] += 1
                DB["metrics"]["receita"] += amount
                DB["orders_db"].append({"email": email, "amount": amount, "timestamp": datetime.now().isoformat()})
                log_event("Sales Agent", "Processar Pagamento", f"COMPRA REAL: +€{amount:.2f} ({email})", is_test=False)

            self._send_json({"ok": True, "message": f"Venda {'[TESTE]' if is_test else '[REAL]'} de €{amount:.2f} processada!"})

        elif self.path == '/api/reset-tests':
            DB["test_metrics"] = {"leads": 0, "vendas": 0, "receita": 0.0}
            DB["test_logs"] = []
            self._send_json({"ok": True, "message": "Testes limpos com sucesso!"})

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
    httpd.serve_forever()
