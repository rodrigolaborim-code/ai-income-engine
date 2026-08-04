# Regras de email

TAG lead -> sequência de educação.
TAG checkout_started -> sequência de intenção.
TAG customer -> onboarding.
TAG refund -> suporte.
TAG upsell_buyer -> remove upsell.
TAG inactive -> reativação.

Pseudo-lógica:
IF customer=true
THEN stop sales_sequence
AND start onboarding

IF refund=true
THEN stop upsell
AND create support_task

IF high_intent=true AND customer=false
THEN send approved_offer_email

IF consent=false
THEN do not subscribe to marketing sequence
