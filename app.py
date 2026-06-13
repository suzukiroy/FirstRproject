import os
import base64
import sqlite3
import json
from datetime import date
from flask import Flask, request, jsonify, render_template, g, send_from_directory
from anthropic import Anthropic

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "ingredients.db")
client = Anthropic()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date TEXT NOT NULL,
            ingredient TEXT NOT NULL,
            quantity REAL,
            unit TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "画像が見つかりません"}), 400

    image_file = request.files["image"]
    image_data = image_file.read()
    image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

    content_type = image_file.content_type or "image/jpeg"
    if content_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        content_type = "image/jpeg"

    prompt = """この写真に写っている食材を分析してください。
見つかった食材を以下のJSON形式で返してください。
単位は g（グラム）、個、本、枚、袋、パック、束など適切なものを使ってください。
量が不明な場合は null にしてください。

{
  "ingredients": [
    {"name": "食材名", "quantity": 数値または null, "unit": "単位"},
    ...
  ]
}

JSONのみを返し、説明文は不要です。"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    text = response.content[0].text.strip()
    # JSONブロックを抽出
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    result = json.loads(text)
    return jsonify(result)


@app.route("/save", methods=["POST"])
def save():
    data = request.get_json()
    record_date = data.get("date", date.today().isoformat())
    ingredients = data.get("ingredients", [])

    if not ingredients:
        return jsonify({"error": "食材データがありません"}), 400

    db = get_db()
    for item in ingredients:
        db.execute(
            "INSERT INTO records (record_date, ingredient, quantity, unit, note) VALUES (?, ?, ?, ?, ?)",
            (
                record_date,
                item.get("name", ""),
                item.get("quantity"),
                item.get("unit", ""),
                item.get("note", ""),
            ),
        )
    db.commit()
    return jsonify({"saved": len(ingredients)})


@app.route("/history")
def history():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM records ORDER BY record_date DESC, id DESC LIMIT 200"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/record/<int:record_id>", methods=["DELETE"])
def delete_record(record_id):
    db = get_db()
    db.execute("DELETE FROM records WHERE id = ?", (record_id,))
    db.commit()
    return jsonify({"deleted": record_id})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
