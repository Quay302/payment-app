import os
import stripe
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# lock to your domain
CORS(app, origins=["https://acwebsite.click"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


# -------------------------
# DATABASE INIT
# -------------------------
def init_db():
    conn = sqlite3.connect("payments.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stripe_id TEXT UNIQUE,
            item TEXT,
            amount REAL,
            status TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()


# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return "Country Club POS Backend Running"


# -------------------------
# CREATE PAYMENT
# -------------------------
@app.route("/pay", methods=["POST"])
def pay():
    data = request.json
    amount = data["amount"]
    item = data.get("item", "unknown")

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


# -------------------------
# WEBHOOK (STORE SALES)
# -------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            endpoint_secret
        )
    except Exception:
        return jsonify({"error": "invalid webhook"}), 400


    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]

        conn = sqlite3.connect("payments.db")
        c = conn.cursor()

        # prevent duplicates
        c.execute("SELECT stripe_id FROM payments WHERE stripe_id = ?", (pi["id"],))
        if c.fetchone():
            return jsonify({"status": "duplicate ignored"})

        c.execute("""
            INSERT INTO payments (stripe_id, item, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            pi["id"],
            "POS SALE",
            pi["amount"] / 100,
            "succeeded",
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)