import os
import logging
import psycopg2
from flask import Flask, render_template, request
from director import analyze_email

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
local_history = []


def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME", "phishingdb"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD")
    )


def save_and_load_rds(result=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id SERIAL PRIMARY KEY,
            sender TEXT,
            subject TEXT,
            score INTEGER,
            is_phishing BOOLEAN
        )
    """)
    if result:
        cur.execute(
            "INSERT INTO scans (sender, subject, score, is_phishing) VALUES (%s, %s, %s, %s)",
            (result["sender"], result["subject"], result["score"], result["is_phishing"])
        )
    conn.commit()
    cur.execute("SELECT sender, subject, score, is_phishing FROM scans ORDER BY id ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"sender": r[0], "subject": r[1], "score": r[2], "is_phishing": r[3]} for r in rows]


@app.route("/health")
def health():
    return "OK", 200


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        file = request.files.get("email_file")
        if file:
            file.save("temp_email.txt")
            result = analyze_email("temp_email.txt")
            app.logger.info(f"Scanned email from {result['sender']} | score={result['score']}")

    if os.environ.get("DB_HOST"):
        history = save_and_load_rds(result)
    else:
        if result:
            local_history.append(result)
        history = local_history

    return render_template("index.html", result=result, history=history)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)