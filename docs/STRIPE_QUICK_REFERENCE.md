# Stripe Integration - Quick Reference & Testing Guide

*AI generated document reviewed and maintained by ma-alves.*

## Quick Start

### 1. Run Migrations
```bash
uv run alembic upgrade head
```

### 2. Configure Stripe Keys
Update `.env`:
```
STRIPE_SECRET_KEY=sk_test_xxxxx (from Stripe Dashboard)
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx (from Stripe Dashboard)
STRIPE_WEBHOOK_SECRET=whsec_xxxxx (from Webhook Endpoint settings)
```

### 3. Start API
```bash
uv run fastapi dev --host 0.0.0.0 --port 8000 --reload
```

### 4. Test Endpoints
Visit: `http://localhost:8000/docs` (Swagger UI)

---

## API Endpoints Reference

### Create Payment Intent
```bash
curl -X POST http://localhost:8000/api/v1/payments/create-payment-intent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rental_id": 1, "save_card": true}'
```
Response:
```json
{
  "client_secret": "pi_xxxxx_secret_xxxxx",
  "payment_intent_id": "pi_xxxxx",
  "amount": 5000,
  "currency": "brl"
}
```

### Retrieve Payment Status
```bash
curl -X GET http://localhost:8000/api/v1/payments/payment-intent/pi_xxxxx \
  -H "Authorization: Bearer $TOKEN"
```

### Capture Payment
```bash
curl -X POST http://localhost:8000/api/v1/payments/capture \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxxxx"}'
```

### Refund Payment
```bash
# Full refund
curl -X POST http://localhost:8000/api/v1/payments/refund \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxxxx"}'

# Partial refund (e.g., R$ 25.00 = 2500 cents)
curl -X POST http://localhost:8000/api/v1/payments/refund \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxxxx", "amount": 2500}'
```

### Create Stripe Customer
```bash
curl -X POST http://localhost:8000/api/v1/payments/create-customer \
  -H "Authorization: Bearer $TOKEN"
```

### List Saved Cards
```bash
curl -X GET http://localhost:8000/api/v1/payments/saved-cards \
  -H "Authorization: Bearer $TOKEN"
```

### Delete Saved Card
```bash
curl -X DELETE http://localhost:8000/api/v1/payments/saved-cards/pm_xxxxx \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing Payment Flows

### Test Case 1: Create Payment for Rental

# Prerequisites: User logged in, Rental created

1. Create Payment Intent
   POST /api/v1/payments/create-payment-intent
   Body: {"rental_id": 1}
   
   ✓ Should return client_secret
   ✓ Should create Payment record with status: PENDING
   ✓ Should create/link StripeCustomer
   ✓ Rental.payment_status should be PENDING

2. (Frontend) Confirm payment with Stripe Elements
   Use client_secret to confirm payment

3. Webhook: Stripe sends payment_intent.succeeded
   ✓ Should update Payment.status to SUCCEEDED
   ✓ Should update Rental.payment_status to SUCCEEDED

4. Capture Payment (if using manual capture)
   POST /api/v1/payments/capture
   Body: {"payment_intent_id": "pi_xxxxx"}
   
   ✓ Should move status to CAPTURED


### Test Case 2: Partial Refund

1. Create and complete payment (as above)

2. Initiate partial refund (e.g., 50% of R$ 100 = 5000 cents)
   POST /api/v1/payments/refund
   Body: {"payment_intent_id": "pi_xxxxx", "amount": 5000}
   
   ✓ Should create Stripe refund
   ✓ Payment.refunded_amount should be 5000
   ✓ Payment.status should be REFUNDED
   ✓ Rental.payment_status should be REFUNDED
   ✓ Customer should receive R$ 50 refund


### Test Case 3: Save and Use Card

1. First payment (setup_future_usage enabled automatically)
   POST /api/v1/payments/create-payment-intent
   
   ✓ Card is automatically saved to StripeCustomer

2. List saved cards
   GET /api/v1/payments/saved-cards
   
   ✓ Should return list with saved card

3. Delete card
   DELETE /api/v1/payments/saved-cards/pm_xxxxx
   
   ✓ Card should be removed from Stripe


### Test Case 4: Failed Payment

1. Use test card that declines: 4000000000000002

2. Frontend confirms payment
   ✓ Payment fails at Stripe

3. Webhook: payment_intent.payment_failed
   ✓ Payment.status should be FAILED
   ✓ Rental.payment_status should be FAILED

---

## Webhook Configuration

### Setup in Stripe Dashboard

1. Go to: Settings → Webhooks
2. Add endpoint:
   - URL: `https://your-domain/api/v1/webhooks/stripe`
   - Version: Latest API version
   - Events to send:
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`
     - `charge.refunded`

3. Copy webhook signing secret to `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   ```

### Testing Webhook Locally (Stripe CLI)

```bash
# 1. Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# 2. Listen for events
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# 3. Trigger test event
stripe trigger payment_intent.succeeded

# 4. Your API should receive and process the webhook
```

---

## Error Scenarios & Status Codes

| Scenario | Status | Response |
|----------|--------|----------|
| Invalid payment method | 400 | `{"detail": "Stripe error message"}` |
| Rental not found | 404 | `{"detail": "Rental not found"}` |
| Not authorized | 403 | `{"detail": "Not authorized to pay for this rental"}` |
| Payment already exists | 400 | `{"detail": "Payment already exists for this rental"}` |
| Refund > payment | 400 | `{"detail": "Refund amount cannot exceed payment amount"}` |
| Invalid webhook sig | 400 | `{"detail": "Invalid signature"}` |
| Stripe API error | 500 | `{"detail": "Stripe error message"}` |

---

## Development & Debugging

### Enable Debug Logging
```python
# In your environment or settings
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Payment Intent Status
```bash
# From Stripe CLI
stripe payment_intents retrieve pi_xxxxx
```

### Test Stripe Connection
```python
from stripe import StripeClient
from app.settings import Settings

client = StripeClient(Settings().STRIPE_SECRET_KEY)

# Create test customer
customer = client.v1.Customer.create(
    email="test@example.com",
    name="Test User"
)
print(customer.id)
```

### View Webhook Events
```bash
# From Stripe Dashboard
Settings → Webhooks → Click your endpoint → View events
```

---

## Migration & Database Updates

### Apply Migration
```bash
uv run alembic upgrade head
```

### Rollback if Needed
```bash
# Last migration
uv run alembic downgrade -1

# Specific revision
uv run alembic downgrade 8a3ea90ea57f
```

### View Current Database Version
```bash
uv run alembic current
```

---

## Performance Tips

1. **Indexing**: Payment queries filtered by rental_id and stripe_payment_intent_id are indexed via unique constraints
2. **Caching**: Consider caching StripeCustomer lookups for frequent users
3. **Batch Processing**: For bulk refunds, consider async job queue (Celery/RQ) #TODO
4. **Idempotency**: All operations use idempotency keys to prevent duplicates on retries

---

## Security Best Practices

Implemented:
- Webhook signature verification required
- User ownership validation on all endpoints
- Sensitive keys in environment variables (never in code)
- Proper error handling without exposing sensitive info

Additional Recommendations (source: Claude Haiku 4.5):
- Enable API key rotation in Stripe Dashboard
- Use restricted API keys (scoped permissions)
- Monitor failed payment attempts for fraud
- Enable 3D Secure for high-value transactions
- Implement rate limiting on payment endpoints

---

## Troubleshooting

### "stripe.StripeClient" not found
✓ Fixed: Now using `stripe.api_key = key`

### Idempotency key errors
✓ Fixed: Implemented `_generate_idempotency_key()` method

### Webhook not receiving events
1. Check webhook signing secret matches `.env`
2. Verify webhook URL is accessible (not localhost in production)
3. Check Stripe Dashboard for failed deliveries
4. Verify events are enabled for your endpoint

### Payment stuck in PENDING
1. Check if webhook was delivered successfully
2. Verify capture was called if using manual capture
3. Check Stripe Dashboard payment intent status

---

## Phase 5 (Testing) - Next Steps

Create unit tests for:
- `test_payment_service.py`: PaymentService methods
- `test_payment_route.py`: Payment endpoints
- Webhook event handling

See project's testing structure in `tests/` directory.

---

## Support & Documentation

- **Stripe Docs**: https://stripe.com/docs/payments
- **Stripe API Reference**: https://stripe.com/docs/api
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Project Tests**: `tests/` directory for examples
- **Payment Analysis**: See `STRIPE_IMPLEMENTATION_SUMMARY.md`
