# Costume Rental API

*Documento parcialmente gerado por IA, revisado e mantido por ma-alves.*

API REST para serviço de aluguel de fantasias construída com FastAPI. Segue arquitetura em camadas: rotas tratam as requisições HTTP, os serviços encapsulam as regras de negócio e o SQLAlchemy define a camada de dados. 

A autenticação e autorização são feitas via JWT com controle de acesso baseado em roles (RBAC) e injeção de dependências nas rotas, possibilitando a fácil extensão de novas roles. Também está integrada com Stripe para processamento de pagamentos dos alugueis e integração com Resend para notificar os clientes por email.

## Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [PostgreSQL](https://www.postgresql.org) - SQL Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL Toolkit e ORM (async)
- [Stripe SDK](https://github.com/stripe/stripe-python) - Pagamentos
- [Resend SDK](https://resend.com/docs/send-with-python) - Email
- [Docker Compose](https://docs.docker.com/compose/) - Ambiente de desenvolvimento
- [GitHub Actions](https://docs.github.com/en/actions) - CI
- [uv](https://github.com/astral-sh/uv) - Package Manager
- [Pytest](https://docs.pytest.org/en/8.2.x/) - Testes
- [PyJWT](https://pypi.org/project/PyJWT/) - Autenticação e Autorização
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) - Migrações

## Estrutura do Projeto
```
app/
  main.py           # Registra os routers
  models.py         # Modelos
  schemas/          # Schemas
  database.py       # DB Generator de sessão assíncrona
  security.py       # Utilitários JWT e senha
  routes/           # Routers da API
  services/         # Camada de lógica de negócio

tests/
  conftest.py       # Fixtures do Pytest
  factories.py      # Utils de fixtures
  test_*_service.py # Testes unitários (mockados)
  test_*_route.py   # Testes de integração

docs/               # Referências
```

## Configuração
1. Clone o repositório:
```sh
git clone https://github.com/ma-alves/costume-rental-api.git
cd costume-rental-api
```
2. Copie as variáveis de ambiente para .env e altere os valores:
```sh
cp .env.example .env
```
3. Build e execução dos containers com Docker Compose:
```sh
docker compose up --build
```
4. O Swagger da API estará disponível em http://localhost:8000/docs

## API Endpoints

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-------------|
| POST | /api/v1/auth/token | No | Get JWT token |
| POST | /api/v1/auth/refresh_token | Admin | Refresh JWT token |
| GET | /api/v1/users | Admin | List all users |
| GET | /api/v1/users/{id} | Admin | Get user by ID |
| POST | /api/v1/users | No | Create new user |
| PUT | /api/v1/users/{id} | Yes | Update user |
| DELETE | /api/v1/users/{id} | Yes | Delete user |
| GET | /api/v1/costumes | No | List costumes |
| GET | /api/v1/costumes/{id} | No | Get costume by ID |
| POST | /api/v1/costumes | Admin | Create costume |
| PUT | /api/v1/costumes/{id} | Admin | Update costume |
| DELETE | /api/v1/costumes/{id} | Admin | Delete costume |
| GET | /api/v1/rental | Admin | List rentals |
| GET | /api/v1/rental/{id} | Admin | Get rental by ID |
| POST | /api/v1/rental | Yes | Create rental |
| DELETE | /api/v1/rental/{id} | Yes | Delete rental |
| POST | /api/v1/payments/create-payment-intent | Yes | Create payment intent |
| GET | /api/v1/payments/payment-intent/{id} | Yes | Retrieve payment intent |
| POST | /api/v1/payments/capture | Yes | Capture payment |
| POST | /api/v1/payments/refund | Yes | Refund payment |
| POST | /api/v1/payments/create-customer | Yes | Create Stripe customer |
| GET | /api/v1/payments/saved-cards | Yes | List saved cards |
| DELETE | /api/v1/payments/saved-cards/{payment_method_id} | Yes | Delete saved card |
| POST | /api/v1/webhooks/stripe | No | Stripe webhook |

## Autenticação e Autorização

A API usa **OAuth2 com Bearer JWT** (`OAuth2PasswordBearer` em [`app/security.py`](app/security.py)). O cliente obtém o token em `POST /api/v1/auth/token` enviando e-mail e senha (`OAuth2PasswordRequestForm`); a senha é validada com **bcrypt** (`passlib`) e o JWT é emitido com o e-mail no claim `sub`, algoritmo e expiração definidos em `.env` (`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_DAYS` — padrão **7 dias**).

### Validação de tokens

`get_current_user` decodifica o Bearer token, busca o usuário no banco pelo e-mail e injeta o `User` na rota. Token inválido, expirado ou usuário inexistente retorna **401** com header `WWW-Authenticate: Bearer`.

### Papéis (RBAC)

O modelo define dois papéis (`Role` em [`app/models.py`](app/models.py)):

| Papel | Valor | Uso típico |
|-------|-------|------------|
| Administrador | `admin` | Catálogo, listagens administrativas, refresh de token |
| Cliente | `customer` | Aluguel, pagamentos, atualização do próprio perfil |

### `RoleChecker`

Em [`app/security.py`](app/security.py), `RoleChecker` é uma dependência callable: recebe a lista de papéis permitidos e, após `get_current_user`, verifica se `current_user.role` está nessa lista. Caso contrário, responde **401** (mesma exceção de credenciais inválidas).

```python
role_checker = Depends(RoleChecker([Role.ADMIN]))
```

Nas rotas, ela é aplicada com `dependencies=[role_checker]` no decorator, sem exigir o usuário como parâmetro da função — apenas garante que quem chama o endpoint é admin.

**Rotas que usam `RoleChecker` (somente `admin`):**

| Router | Endpoints |
|--------|-----------|
| [`auth_route.py`](app/routes/auth_route.py) | `POST /refresh_token` |
| [`user_route.py`](app/routes/user_route.py) | `GET /`, `GET /{user_id}` |
| [`costume_route.py`](app/routes/costume_route.py) | `POST /`, `PUT /{id}`, `DELETE /{id}` |
| [`rental_route.py`](app/routes/rental_route.py) | `GET /`, `GET /{rental_id}` |

**Rotas autenticadas sem `RoleChecker`** — qualquer usuário logado (`Depends(get_current_user)` via `CurrentUser`):

| Router | Endpoints |
|--------|-----------|
| [`user_route.py`](app/routes/user_route.py) | `PUT /{user_id}`, `DELETE /{user_id}` (regras adicionais no serviço) |
| [`rental_route.py`](app/routes/rental_route.py) | `POST /`, `DELETE /{rental_id}` |
| [`payment_route.py`](app/routes/payment_route.py) | Todos os endpoints de pagamento e cartões salvos |

**Endpoints públicos** (sem JWT): `POST /api/v1/auth/token`, `POST /api/v1/users`, leitura do catálogo de fantasias (`GET /costumes`), `POST /api/v1/webhooks/stripe`.

## Integração com Stripe

Pagamentos são processados via [Stripe](https://stripe.com) SDK através de `PaymentService` em [`app/services/payment_service.py`](app/services/payment_service.py). A integração cobre desde a criação de *payment intents* até webhooks para atualização de status e salvamento de cartões.

### Arquitetura

O `PaymentService` utiliza `StripeClient` (SDK v1, não `stripe.api_key`) e encapsula chamadas síncronas ao Stripe em métodos privados. As rotas públicas (`payment_route.py`) e o webhook (`webhook_route.py`) orquestram o fluxo de negócio.

| Camada | Responsabilidade |
|--------|-----------------|
| [`app/services/payment_service.py`](app/services/payment_service.py) | Lógica de negócio + chamadas Stripe via `StripeClient` |
| [`app/routes/payment_route.py`](app/routes/payment_route.py) | Endpoints REST para clientes (criar, capturar, reembolsar, cartões) |
| [`app/routes/webhook_route.py`](app/routes/webhook_route.py) | Verificar assinatura Stripe, atualizar DB, agendar emails |
| [`app/models.py`](app/models.py) | Modelos `Payment`, `StripeCustomer`, enum `PaymentStatus` |
| [`app/settings.py`](app/settings.py) | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` |

### Configuração

Adicione ao `.env` (veja [`.env.example`](.env.example)):

```env
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_public_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

| Variável | Finalidade |
|----------|------------|
| `STRIPE_SECRET_KEY` | Chave secreta do Stripe (server-side) |
| `STRIPE_PUBLISHABLE_KEY` | Chave pública para o frontend (Stripe.js) |
| `STRIPE_WEBHOOK_SECRET` | Segredo para verificar assinatura de webhooks |

### Modelos de Dados

| Modelo | Tabela | Finalidade |
|--------|--------|------------|
| `Payment` | `payments` | Vincula rental a um payment intent do Stripe, controla status e valores |
| `StripeCustomer` | `stripe_customers` | Associa um `User` local a um `customer_id` do Stripe (1:1) |
| `PaymentStatus` | enum | `PENDING`, `SUCCEEDED`, `CAPTURED`, `FAILED`, `REFUNDED` |

### PaymentService

`PaymentService` expõe métodos públicos assíncronos que combinam validação de negócio com chamadas privadas síncronas ao Stripe:

| Método público | Endpoint | Descrição |
|----------------|----------|-----------|
| `create_payment_intent` | `POST /payments/create-payment-intent` | Verifica rental, cria/get StripeCustomer, cria payment intent com `capture_method: manual` e `setup_future_usage: off_session` |
| `retrieve_payment_intent` | `GET /payments/payment-intent/{id}` | Busca status do payment intent no Stripe |
| `capture_payment` | `POST /payments/capture` | Captura pagamento autorizado |
| `refund_payment` | `POST /payments/refund` | Reembolso total ou parcial com validação de valor |
| `create_customer` | `POST /payments/create-customer` | Cria StripeCustomer explicitamente |
| `list_saved_cards` | `GET /payments/saved-cards` | Lista cartões salvos do cliente |
| `delete_saved_card` | `DELETE /payments/saved-cards/{id}` | Remove cartão salvo |

Características importantes:

- **Idempotency keys** — toda operação usa `_generate_idempotency_key` para evitar duplicatas em retentativas
- **`capture_method: manual`** — o valor é autorizado mas não capturado automaticamente; a captura é feita sob demanda
- **`setup_future_usage: off_session`** — cartão é salvo automaticamente no StripeCustomer para aluguéis futuros
- **Status mapping** — `_get_payment_status_enum` converte status do Stripe para o enum local

### Fluxo de Pagamento

1. **Cliente inicia** → `POST /create-payment-intent` → cria `Payment` (status: `PENDING`) e retorna `client_secret`
2. **Frontend confirma** → Stripe Elements confirma o payment intent com o cartão
3. **Webhook notifica** → `payment_intent.succeeded` → atualiza `Payment` (status: `SUCCEEDED`) e `Rental.payment_status`
4. **Captura** (opcional) → `POST /capture` → move para `CAPTURED`
5. **Reembolso** → `POST /refund` → total ou parcial, status `REFUNDED`

### Webhook

`POST /api/v1/webhooks/stripe` em [`app/routes/webhook_route.py`](app/routes/webhook_route.py) processa eventos:

| Evento Stripe | Ação no DB |
|---------------|------------|
| `payment_intent.succeeded` | `Payment.status → SUCCEEDED`, `Rental.payment_status → SUCCEEDED` |
| `payment_intent.payment_failed` | `Payment.status → FAILED`, `Rental.payment_status → FAILED` |
| `charge.refunded` | `Payment.status → REFUNDED`, atualiza `refunded_amount` |

A assinatura é verificada com `STRIPE_WEBHOOK_SECRET`; payloads inválidos retornam `400`.

### Testes de pagamento

```sh
uv run pytest tests/test_payment_service.py tests/test_payment_route.py -vv
```

### Webhook Testing (Stripe CLI)

```sh
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
stripe trigger payment_intent.succeeded
```

## Integração com Resend

E-mails transacionais são enviados via [Resend](https://resend.com) SDK através de `EmailService` em [`app/services/email_service.py`](app/services/email_service.py), seguindo o mesmo padrão service-layer do `PaymentService` com Stripe.

### Arquitetura

Webhooks do Stripe disparam e-mails **após** a atualização do banco, usando `BackgroundTasks` do FastAPI — o Stripe recebe `200` rápido e falhas no Resend nunca revertem o estado do pagamento.

| Camada | Responsabilidade |
|--------|-----------------|
| [`app/routes/webhook_route.py`](app/routes/webhook_route.py) | Verificar assinatura Stripe, atualizar DB, agendar tarefas de email |
| [`app/services/email_service.py`](app/services/email_service.py) | Carregar dados, renderizar HTML, chamar Resend, tratar erros em background |
| [`app/email_templates/`](app/email_templates/) | Templates HTML Jinja2 |
| [`app/settings.py`](app/settings.py) | `RESEND_API_KEY`, `EMAIL_FROM` |

### Configuração

Adicione ao `.env` (veja [`.env.example`](.env.example)):

```env
RESEND_API_KEY=re_xxxxxxxxxxxx
EMAIL_FROM=Costume Rental <noreply@yourdomain.com>
```

| Variável | Finalidade |
|----------|------------|
| `RESEND_API_KEY` | API key do dashboard do Resend |
| `EMAIL_FROM` | `Nome <email@domain>` usado no campo `from` de cada envio |

Para teste local sem domínio verificado, o Resend permite `onboarding@resend.dev` como remetente.

### EmailService

`EmailService` é um singleton que configura a chave da API e expõe métodos públicos para cada evento de negócio:

| Método | Disparado por | Template |
|--------|---------------|----------|
| `send_payment_receipt_by_payment_id` | `payment_intent.succeeded` | `payment_receipt.html` |
| `send_payment_failed_by_payment_id` | `payment_intent.payment_failed` | `payment_failed.html` |
| `send_refund_notice_by_payment_id` | `charge.refunded` | `refund_notice.html` |

Cada método abre uma sessão própria do banco (a sessão da request já foi fechada), carrega `Payment` + `Rental` + `User`, renderiza o template HTML com Jinja2 e chama `resend.Emails.send`. Erros `ResendError` são logados, nunca viram `HTTPException`, o background task não tem cliente HTTP para responder.

### Agendamento no webhook

Em [`app/routes/webhook_route.py`](app/routes/webhook_route.py), cada handler privado retorna `payment.id` ou `None`:

```python
payment_id = await _handle_payment_succeeded(payment_intent, session)
if payment_id:
    background_tasks.add_task(
        email_service.send_payment_receipt_by_payment_id,
        payment_id,
    )
```

Regras:
1. Agendar somente quando `payment_id` não for `None`.
2. Handlers fazem commit antes de retornar o ID; a tarefa roda após a resposta do webhook.
3. Falhas de email nunca alteram o HTTP status do webhook.

### Testes de envio de email

`tests/test_email_service.py` cobre renderização de templates, `_send` com `resend.Emails.send` mockado, e cada método público (sucesso, `ResendError` engolido, skip quando payment não existe).

```sh
uv run pytest tests/test_email_service.py -vv
```

## Testes

Usa Pytest com banco de dados SQLite em memória para execuções de teste rápidas e isoladas. As fixtures em conftest.py fornecem dados de teste e gerenciamento de sessão.

```sh
# Executar todos os testes
uv run pytest -s -x -vv

# Executar com coverage
uv run pytest -s -x --cov=app -vv

# Executar arquivo de teste específico
uv run pytest tests/test_user_route.py -vv
```

Estrutura de testes por domínio:
- `test_*_service.py` - Testes unitários com sessões de banco mockadas
- `test_*_route.py` - Testes de integração com TestClient

## Exemplos
### List Costumes
```sh
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/costumes/' \
  -H 'accept: application/json'
```

Response:
```json
{
  "costumes": [
    {
      "id": 1,
      "name": "Batman Suit",
      "description": "Full Batman costume",
      "fee": 150.00,
      "availability": "available"
    }
  ]
}
```

### Create Rental
```sh
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/rental/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{
  "costume_id": 1,
  "customer_id": 2
}'
```

Response:
```json
{
  "rental_date": "2024-12-25T10:00:00",
  "return_date": "2025-01-01T10:00:00",
  "costume": {
    "id": 1,
    "name": "Batman Suit",
    "description": "Full Batman costume",
    "fee": 150.00,
    "availability": "unavailable"
  },
  "user": {
    "id": 2,
    "name": "Matheus Alves",
    "email": "matheus@example.com",
    "phone": "12345678901",
    "role": "customer"
  }
}
```
