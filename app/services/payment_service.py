import stripe
from app.settings import Settings


class PaymentService:
    def __init__(self):
        self.client = stripe.StripeClient(Settings().STRIPE_SECRET_KEY)

    # pode passar user attributes
    def create_customer(self, email: str, name: str):
        try:
            customer = self.client.v1.customers.create(params={
                "email": email,
                "name": name,
            })
        except stripe.StripeError as e:
            return str(e)
    
        return customer.id  # store this in your DB, reuse on future payments

    # botar payload pra tude
    def create_payment_intent(
        self,
        amount: int,
        currency: str = "brl",
        customer_id: str = "",
    ):
        try:
            payment_intent = self.client.v1.payment_intents.create(params={
                "amount": amount,  # in cents, e.g. 5000 = R$50.00
                "currency": currency,
                "customer": customer_id,
                "payment_method_types": ["card"],
                "capture_method": "manual",
                "setup_future_usage": "off_session",
                "metadata": {
                    "costume_id": "#TODO",
                    "rental_period": "#TODO",
                },
            })
        except stripe.StripeError as e:
            return str(e)

        return payment_intent.client_secret, payment_intent.id