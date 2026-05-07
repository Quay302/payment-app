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
        return jsonify({"error": "empty cart"}), 400

    line_items = []

    for item in items:
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": item["name"]
                },
                "unit_amount": int(item["price"] * 100)
            },
            "quantity": 1
        })

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url="https://acwebsite.click/success.html",
        cancel_url="https://acwebsite.click/cancel.html"
    )

    return jsonify({"url": session.url})


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

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        conn = sqlite3.connect("payments.db")
        c = conn.cursor()

        c.execute("""
            INSERT OR IGNORE INTO orders (
                stripe_session_id,
                amount,
                items,
                status,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            session["id"],
            session["amount_total"] / 100,
            str(session.get("metadata", {})),
            "paid",
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        print("ORDER SAVED:", session["id"])

    return jsonify({"status": "ok"})

@app.route("/admin/orders")
def admin_orders():
    conn = sqlite3.connect("payments.db")
    c = conn.cursor()

    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()

    conn.close()

    html = "<h1>POS Dashboard</h1>"

    total_revenue = 0

    for r in rows:
        total_revenue += r[2]
        html += f"""
        <div style='border:1px solid #ddd;padding:10px;margin:10px'>
            <b>Order:</b> {r[0]} <br>
            <b>Amount:</b> ${r[2]} <br>
            <b>Status:</b> {r[4]} <br>
            <b>Items:</b> {r[3]} <br>
            <b>Date:</b> {r[5]}
        </div>
        """

    html += f"<h2>Total Revenue: ${total_revenue}</h2>"

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)