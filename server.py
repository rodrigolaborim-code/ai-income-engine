import http.server
import socketserver
import json
import os
import time
import threading
import random
from datetime import datetime

PORT = int(os.environ.get("PORT", 8000))
DB_FILE = "banco de dados.json"

def carregar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
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

def guardar_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Erro ao guardar BD:", e)

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
        DB["test_logs"].insert(0, log_entry)
        DB["test_logs"] = DB["test_logs"][:15]
    else:
        DB["logs"].insert(0, log_entry)
        DB["logs"] = DB["logs"][:20]
    
    guardar_db()

def run_autonomous_agents():
    tipos_conteudo = [
        {"tipo": "E-Book / Livro", "titulo": "Manual Prático de Automação com IA (PDF)", "detalhe": "Livro digital de 45 páginas gerado com estratégias de workflows."},
        {"tipo": "Vídeo / VSL", "titulo": "Vídeo de Vendas: Como Escalar com Agentes IA", "detalhe": "Roteiro e animação renderizada para anúncios de alta conversão."},
        {"tipo": "Imagem / Criativo", "titulo": "Pack de Criativos para Anúncios (Ads)", "detalhe": "Banner cyberpunk gerado por IA para campanhas de tráfego pago."},
        {"tipo": "Copy / E-mail", "titulo": "Sequência de E-mails de Boas-Vindas", "detalhe": "5 e-mails automatizados para conversão de leads frios em clientes."}
    ]

    while True:
        time.sleep(15)
        agente_choice = random.choice(["Research", "Content", "Funnel", "Analytics"])

        if agente_choice == "Research":
            log_event("Research Agent", "Análise de Mercado", "Nova oportunidade mapeada: Templates de IA para PMEs")
        elif agente_choice == "Content":
            item_escolhido = random.choice(tipos_conteudo)
            DB["metrics"]["conteudos"] += 1
            
            content_item = {
                "hora": datetime.now().strftime("%H:%M:%S"),
                "agente": "Content Agent",
                "tipo": item_escolhido["tipo"],
                "titulo": item_escolhido["titulo"],
                "conteudo": item_escolhido["detalhe"],
                "created_at": datetime.now().isoformat()
            }
            DB["content_db"].insert(0, content_item)
            DB["content_db"] = DB["content_db"][:30]
            guardar_db()
            log_event("Content Agent", f"Criação de {item_escolhido['tipo']}", f"Gerado: {item_escolhido['titulo']}")
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
            response_data = DB.copy()
            response_data["contents"] = DB["content_db"]
            self._send_json(response_data)
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

        elif self.path in ['/lead', '/api/lead']:
            email = payload.get('email', 'teste@lead.com').strip().lower()

            if is_test:
                DB["test_metrics"]["leads"] += 1
                guardar_db()
                log_event("Funnel Agent", "Simulação Lead", f"TESTE: Lead registado ({email})", is_test=True)
            else:
                DB["metrics"]["leads"] += 1
                DB["leads_db"].append({"email": email, "created_at": datetime.now().isoformat()})
                guardar_db()
                log_event("Funnel Agent", "Captura de Lead", f"Novo Lead Registado: {email}", is_test=False)

            self._send_json({"ok": True, "message": f"Lead {'[TESTE]' if is_test else '[REAL]'} guardada com sucesso!"})

        elif self.path in ['/purchase', '/api/purchase']:
            email = payload.get('email', 'teste@venda.com').strip().lower()
            amount = float(payload.get('amount', 29.0))

            if is_test:
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
    httpd.serve_forever()
