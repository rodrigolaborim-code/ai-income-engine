# Webhook contracts

## POST /lead
Required:
email, consent
Optional:
first_name, source, medium, campaign, content_id

## POST /purchase
Required:
event, order_id, email, amount, currency, product_id
Allowed event:
purchase, refund, chargeback

## POST /content-approved
Required:
content_id, status
Allowed status:
approved, rejected

## POST /feedback
Required:
email_or_order_id, message
Optional:
rating, product_id

### Segurança
- Verificar assinatura do fornecedor de checkout quando existir.
- Não confiar no valor recebido sem validação.
- Não guardar dados desnecessários.
- Limitar acesso às bases.
- Não colocar API keys em prompts ou ficheiros públicos.
