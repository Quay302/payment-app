import os
import stripe
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Allow your domain
CORS(app, origins=["https://acwebsite.click"])

# Stripe keys
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


# -------------------------
# DATABASE
# -------------------------
def init_db():
    conn = sqlite3.connect("payments.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stripe_id TEXT UNIQUE,
            amount REAL,
            items TEXT,
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
# CREATE PAYMENT INTENT
# -------------------------
@app.route("/pay", methods=["POST"])
def pay():
    data = request.json
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "Cart is empty"}), 400

    try:
        line_items = []

        for item in items:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item["name"],
                    },
                    "unit_amount": int(item["price"] * 100),
                },
                "quantity": 1,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url="https://acwebsite.click/success.html",
            cancel_url="https://acwebsite.click/cancel.html"
        )

        return jsonify({"url": session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -------------------------
# WEBHOOK
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

        # avoid duplicates
        c.execute("SELECT stripe_id FROM payments WHERE stripe_id = ?", (pi["id"],))
        if c.fetchone():
            return jsonify({"status": "duplicate ignored"})

        c.execute("""
            INSERT INTO payments (stripe_id, amount, items, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            pi["id"],
            pi["amount"] / 100,
            str(pi.get("metadata", {}).get("items", "")),
            "succeeded",
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        print("Saved payment:", pi["id"])

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)