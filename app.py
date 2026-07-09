from flask import Flask, render_template, request, jsonify
import sqlite3
import time

app = Flask(__name__)

DB_NAME = "timer.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT UNIQUE NOT NULL,
            total_seconds INTEGER DEFAULT 0,
            running_since INTEGER DEFAULT NULL,
            current_timer_name TEXT DEFAULT NULL,
            last_timer_name TEXT DEFAULT NULL
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()

    if not nickname:
        return jsonify({"error": "Nickname obbligatorio"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (
            nickname,
            total_seconds,
            running_since,
            current_timer_name,
            last_timer_name
        )
        VALUES (?, 0, NULL, NULL, NULL)
    """, (nickname,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Utente registrato", "nickname": nickname})


@app.route("/api/start", methods=["POST"])
def start_timer():
    data = request.get_json()

    nickname = data.get("nickname", "").strip()
    timer_name = data.get("timer_name", "").strip()

    if not nickname:
        return jsonify({"error": "Nickname obbligatorio"}), 400

    if not timer_name:
        return jsonify({"error": "Nome timer obbligatorio"}), 400

    now = int(time.time())

    conn = get_db()
    cursor = conn.cursor()

    user = cursor.execute("""
        SELECT * FROM users WHERE nickname = ?
    """, (nickname,)).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Utente non trovato"}), 404

    if user["running_since"] is not None:
        conn.close()
        return jsonify({"message": "Timer già attivo"})

    cursor.execute("""
        UPDATE users
        SET running_since = ?,
            current_timer_name = ?
        WHERE nickname = ?
    """, (now, timer_name, nickname))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Timer avviato",
        "timer_name": timer_name
    })


@app.route("/api/stop", methods=["POST"])
def stop_timer():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()

    now = int(time.time())

    conn = get_db()
    cursor = conn.cursor()

    user = cursor.execute("""
        SELECT * FROM users WHERE nickname = ?
    """, (nickname,)).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Utente non trovato"}), 404

    if user["running_since"] is None:
        conn.close()
        return jsonify({"message": "Timer non attivo"})

    elapsed = now - user["running_since"]
    new_total = user["total_seconds"] + elapsed

    cursor.execute("""
        UPDATE users
        SET total_seconds = ?,
            running_since = NULL,
            last_timer_name = current_timer_name,
            current_timer_name = NULL
        WHERE nickname = ?
    """, (new_total, nickname))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Timer fermato",
        "elapsed_seconds": elapsed,
        "total_seconds": new_total
    })


@app.route("/api/reset", methods=["POST"])
def reset_timer():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET total_seconds = 0,
            running_since = NULL,
            current_timer_name = NULL,
            last_timer_name = NULL
        WHERE nickname = ?
    """, (nickname,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Timer azzerato"})


@app.route("/api/leaderboard")
def leaderboard():
    now = int(time.time())

    conn = get_db()
    cursor = conn.cursor()

    users = cursor.execute("""
        SELECT nickname, total_seconds, running_since, current_timer_name, last_timer_name
        FROM users
    """).fetchall()

    conn.close()

    result = []

    for user in users:
        total = user["total_seconds"]
        running = user["running_since"] is not None

        if running:
            total += now - user["running_since"]

        result.append({
            "nickname": user["nickname"],
            "total_seconds": total,
            "running": running,
            "current_timer_name": user["current_timer_name"],
            "last_timer_name": user["last_timer_name"]
        })

    result.sort(key=lambda x: x["total_seconds"], reverse=True)

    return jsonify(result)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5003, use_reloader=False)
