# Email Service Implementation Plan — Resend

*AI generated document reviewed and maintained by ma-alves.*

## Overview

Add transactional email capabilities using [Resend](https://resend.com) (3,000 emails/month free). The implementation follows the same service-layer pattern as `PaymentService`: a class-based `EmailService` with private helpers for HTTP calls and async public methods for business logic.

---

## 1. Dependencies

**No new dependencies needed.** `httpx` is already in the project (`httpx>=0.28.1`) and will be used to call the Resend REST API.

For HTML templates, use `Jinja2` — it is available as a transitive dependency of `FastAPI[standard]` (already installed).

---

## 2. Settings (`app/settings.py`)

Add one new field to `Settings`:

```python
RESEND_API_KEY: str
```

**.env addition:**
```
RESEND_API_KEY=re_xxxxxxxxxxxx
```

Resend also requires a verified domain or the default `onboarding@resend.dev` for testing.

---

## 3. Schemas (`app/schemas/email_schema.py`)

```python
from pydantic import BaseModel, EmailStr


class EmailAddress(BaseModel):
    email: EmailStr
    name: str | None = None


class SendEmailRequest(BaseModel):
    to: list[EmailAddress]
    subject: str
    html: str
    from_: str = 'Costume Rental <noreply@yourdomain.com>'

    # Optional: support text fallback, reply-to, etc.
    text: str | None = None


class SendEmailResponse(BaseModel):
    id: str
```

---

## 4. Email Templates (`app/email_templates/`)

Create a directory for HTML templates:

```
app/
  email_templates/
    welcome.html          # Sent after user registration
    rental_confirmation.html  # Sent after rental is created
    payment_receipt.html  # Sent after payment is captured
    rental_reminder.html  # Sent before return date
```

Each template receives template variables (e.g., `{{ user.name }}`, `{{ rental.id }}`). Templates are loaded once at module level using Jinja2's `FileSystemLoader`.

---

## 5. EmailService (`app/services/email_service.py`)

Structure exactly mirrors `PaymentService`:

```python
from jinja2 import Environment, FileSystemLoader
from fastapi import HTTPException


class EmailService:
    def __init__(self):
        self.api_key = Settings().RESEND_API_KEY
        self.base_url = 'https://api.resend.com'
        self.template_env = Environment(
            loader=FileSystemLoader('app/email_templates'),
        )

    # --- Private helpers ---

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 template. Kept as a private method for testability."""
        try:
            template = self.template_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Template error: {e}')

    def _send(self, payload: dict) -> dict:
        """Sync HTTP call to Resend API. Returns response body."""
        try:
            with httpx.Client() as client:
                response = client.post(
                    f'{self.base_url}/emails',
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f'Resend API error: {e.response.text}',
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f'Email request failed: {e}')

    # --- Public methods ---

    async def send_welcome_email(self, user: User) -> SendEmailResponse:
        """Send welcome email after user registration."""
        html = self._render_template('welcome.html', {'name': user.name})
        result = self._send({
            'from': 'Costume Rental <noreply@yourdomain.com>',
            'to': [user.email],
            'subject': 'Welcome to Costume Rental!',
            'html': html,
        })
        return SendEmailResponse(id=result['id'])

    async def send_rental_confirmation(
        self, user: User, rental: Rental
    ) -> SendEmailResponse:
        """Send confirmation after rental is created."""
        html = self._render_template('rental_confirmation.html', {
            'name': user.name,
            'rental_id': rental.id,
            'costume_name': rental.costumes.name,
            'rental_date': rental.rental_date,
            'return_date': rental.return_date,
            'fee': rental.costumes.fee,
        })
        result = self._send({
            'from': 'Costume Rental <noreply@yourdomain.com>',
            'to': [user.email],
            'subject': f'Rental #{rental.id} Confirmed',
            'html': html,
        })
        return SendEmailResponse(id=result['id'])

    async def send_payment_receipt(
        self, user: User, payment: Payment, rental: Rental
    ) -> SendEmailResponse:
        """Send receipt after payment is captured."""
        html = self._render_template('payment_receipt.html', {
            'name': user.name,
            'rental_id': rental.id,
            'amount': payment.amount / 100,
            'currency': payment.currency.upper(),
            'payment_intent_id': payment.stripe_payment_intent_id,
        })
        result = self._send({
            'from': 'Costume Rental <noreply@yourdomain.com>',
            'to': [user.email],
            'subject': f'Payment Receipt — R$ {payment.amount / 100:.2f}',
            'html': html,
        })
        return SendEmailResponse(id=result['id'])

    async def send_rental_reminder(
        self, user: User, rental: Rental
    ) -> SendEmailResponse:
        """Send reminder that return date is approaching."""
        html = self._render_template('rental_reminder.html', {
            'name': user.name,
            'rental_id': rental.id,
            'costume_name': rental.costumes.name,
            'return_date': rental.return_date,
        })
        result = self._send({
            'from': 'Costume Rental <noreply@yourdomain.com>',
            'to': [user.email],
            'subject': f'Reminder: Return {rental.costumes.name} Soon',
            'html': html,
        })
        return SendEmailResponse(id=result['id'])
```

---

## 6. Route (`app/routes/email_route.py`)

The route is minimal — most sends are triggered internally by other services. An admin-only test endpoint is useful for verification:

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, Role
from app.security import get_current_user
from app.services.email_service import EmailService
from app.schemas.email_schema import SendEmailResponse

router = APIRouter(prefix='/api/v1/emails', tags=['emails'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
email_service = EmailService()


@router.post('/test-welcome', response_model=SendEmailResponse)
async def test_welcome(current_user: CurrentUser):
    """Send welcome email to current user (for testing)."""
    return await email_service.send_welcome_email(current_user)
```

---

## 7. Integration Points

Emails should be triggered from existing services via `BackgroundTasks` to avoid blocking the response:

### After user registration (`app/services/user_service.py`)
```python
from fastapi import BackgroundTasks
from app.services.email_service import EmailService


async def create_user(self, session, request, background_tasks: BackgroundTasks):
    user = User(...)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    # Fire-and-forget: send later, don't block the response
    background_tasks.add_task(
        EmailService().send_welcome_email, user
    )
    return user
```

### After payment capture (`app/services/payment_service.py`)
```python
background_tasks.add_task(
    EmailService().send_payment_receipt, current_user, payment, rental
)
```

### Router registration in `app/main.py` (optional — only needed if exposing endpoints)
```python
from .routes import auth_route, costume_route, rental_route, user_route, payment_route, webhook_route, email_route

app.include_router(email_route.router)
```

---

## 8. Email Templates

### `app/email_templates/welcome.html`
```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h1>Welcome, {{ name }}!</h1>
  <p>Thank you for joining Costume Rental. Browse our catalog and find the perfect costume for any occasion.</p>
  <a href="https://yourdomain.com/costumes" style="display: inline-block; padding: 12px 24px; background: #6C5CE7; color: white; text-decoration: none; border-radius: 6px;">
    Browse Costumes
  </a>
</body>
</html>
```

### `app/email_templates/rental_confirmation.html`
```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h1>Rental Confirmed!</h1>
  <p>Hi {{ name }},</p>
  <p>Your rental has been confirmed:</p>
  <ul>
    <li><strong>Costume:</strong> {{ costume_name }}</li>
    <li><strong>Rental Date:</strong> {{ rental_date }}</li>
    <li><strong>Return Date:</strong> {{ return_date }}</li>
    <li><strong>Fee:</strong> R$ {{ "%.2f"|format(fee) }}</li>
  </ul>
</body>
</html>
```

### `app/email_templates/payment_receipt.html`
```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h1>Payment Received</h1>
  <p>Hi {{ name }},</p>
  <p>Your payment for rental #{{ rental_id }} has been processed.</p>
  <ul>
    <li><strong>Amount:</strong> {{ currency }} {{ "%.2f"|format(amount) }}</li>
    <li><strong>Payment ID:</strong> {{ payment_intent_id }}</li>
  </ul>
</body>
</html>
```

### `app/email_templates/rental_reminder.html`
```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h1>Return Reminder</h1>
  <p>Hi {{ name }},</p>
  <p>This is a reminder that <strong>{{ costume_name }}</strong> is due back on <strong>{{ return_date }}</strong>.</p>
  <p>Please return it on time to avoid late fees.</p>
</body>
</html>
```

---

## 9. Testing

### Unit tests (`tests/test_email_service.py`)
- Mock `httpx.Client.post` (or patch `EmailService._send`) to avoid real API calls
- Test template rendering with known context
- Test error handling (Resend API returns 4xx/5xx)
- Follow the same pattern as `tests/test_payment_service.py`:
  - `_make_service()` helper that sets `service.client` to a `MagicMock`
  - `@patch.object(EmailService, '_send')` for public method tests

### Test example:
```python
def test_send_welcome_email_success(self):
    mock_user = MagicMock(spec=User)
    mock_user.name = 'Test'
    mock_user.email = 'test@example.com'

    service = self._make_service()
    service._send = MagicMock(return_value={'id': 'email_123'})

    result = service.send_welcome_email(mock_user)

    assert result.id == 'email_123'
    service._send.assert_called_once()
```

---

## 10. Files to Create/Modify

| File | Action |
|------|--------|
| `app/settings.py` | Add `RESEND_API_KEY: str` |
| `app/schemas/email_schema.py` | Create — Pydantic schemas |
| `app/services/email_service.py` | Create — `EmailService` class |
| `app/routes/email_route.py` | Create — test endpoint (optional) |
| `app/main.py` | Add `email_route` import (optional) |
| `app/email_templates/welcome.html` | Create |
| `app/email_templates/rental_confirmation.html` | Create |
| `app/email_templates/payment_receipt.html` | Create |
| `app/email_templates/rental_reminder.html` | Create |
| `tests/test_email_service.py` | Create — unit tests |
| `.env.example` | Add `RESEND_API_KEY` |

No new dependencies required (`httpx` + `Jinja2` already available).

---

## 11. Resend Setup

1. Sign up at https://resend.com
2. Add and verify a domain (or use `onboarding@resend.dev` for testing)
3. Create an API key in Dashboard → API Keys
4. Add `RESEND_API_KEY=re_xxxxxxxx` to `.env`
