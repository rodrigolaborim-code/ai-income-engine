# Make — construção dos cenários

O Make permite usar agentes com módulos, cenários e MCP como ferramentas. Para cenários usados como ferramentas de agentes, os inputs/outputs devem ser definidos e o cenário deve estar preparado para execução on-demand. citeturn0search2turn0search5

## Cenário A01 — New Lead
1. Webhooks > Custom webhook
2. Tools > Set variables
3. Data Store/CRM > Create record
4. Email > Send message
5. Email/CRM > Add tag
6. Response

Webhook payload:
{
  "email": "cliente@example.com",
  "first_name": "Nome",
  "source": "instagram",
  "campaign": "ai-launch",
  "consent": true
}

## Cenário A03 — Purchase
1. Webhook
2. Router
3. Filter event=purchase
4. Save order
5. Delivery action
6. Remove sales tag
7. Add customer tag
8. Onboarding email

## Cenário A06 — Weekly Analytics
1. Scheduler
2. Pull metrics
3. Aggregator
4. Run AI Agent
5. Save report
6. Send owner notification

Para tarefas determinísticas como sincronizar compras ou atualizar CRM, usa cenário normal; para classificação, análise e geração variável, usa agente. citeturn0search0
