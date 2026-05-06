import os
import stripe
from flask import Flask, request, jsonify

app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


# --- Homepage route ---
@app.route("/")
def home():
    return "Backend is running"


# --- Payment Intent endpoint ---
@app.route("/pay", methods=["POST"])
def pay():
    data = request.json
    amount = data["amount"]

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            automatic_payment_methods={"enabled": True}
        )

        return jsonify({
            "clientSecret": intent.client_secret
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- Webhook endpoint (PRODUCTION CRITICAL) ---
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )

    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400

    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    # --- Handle events ---
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        print(f"Payment succeeded: {payment_intent['id']}")

    elif event["type"] == "payment_intent.payment_failed":
        print("Payment failed")

    return jsonify({"status": "success"})