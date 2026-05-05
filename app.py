from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Backend is running"

@app.route("/pay", methods=["POST"])
def pay():
    data = request.get_json()

    if not data or "amount" not in data:
        return jsonify({"error": "Invalid request"}), 400

    return jsonify({"message": "received", "amount": data["amount"]})

if __name__ == "__main__":
    app.run(debug=True)
    app.run(host="0.0.0.0", port=5000)