from flask import Flask, jsonify, request


app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    message = payload.get("message")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message is required"}), 400

    return jsonify(
        {
            "message": "This is a placeholder response from the Python backend. Future versions will replace this with research and writing assistance."
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
