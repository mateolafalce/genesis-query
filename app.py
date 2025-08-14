import os
import sqlite3
import math
from flask import Flask, render_template, redirect, url_for, session, request, g, flash, jsonify
from dotenv import load_dotenv
import requests

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")
DATABASE = 'database.db'
MAX_COMMENT_LENGTH = 512
PER_PAGE = 20

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.route('/')
def home():
    db = get_db()
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * PER_PAGE

    propuestas_cursor = db.execute(
        'SELECT id, content, votes, country_code FROM comments ORDER BY votes DESC LIMIT ? OFFSET ?',
        (PER_PAGE, offset)
    )
    propuestas = [
        dict(p) | {"emoji": country_code_to_emoji(p["country_code"])}
        for p in propuestas_cursor.fetchall()
    ]

    ip_address = get_real_ip()
    comments_cursor = db.execute(
        'SELECT id, content, votes, country_code FROM comments WHERE ip_address = ? ORDER BY created_at DESC',
        (ip_address,)
    )
    comments = [
        dict(c) | {"emoji": country_code_to_emoji(c["country_code"])}
        for c in comments_cursor.fetchall()
    ]

    total_propuestas = db.execute('SELECT COUNT(*) FROM comments').fetchone()[0]
    has_next = offset + PER_PAGE < total_propuestas
    has_prev = page > 1

    return render_template(
        'index.html',
        propuestas=propuestas,
        comments=comments,
        page=page,
        has_next=has_next,
        has_prev=has_prev
    )

@app.route("/comentar", methods=["POST"])
def comentar():
    ip_address = get_real_ip()
    country_code = get_country_code(ip_address)
    db = get_db()
    existing_comment = db.execute('SELECT id FROM comments WHERE ip_address = ?', (ip_address,)).fetchone()
    if existing_comment:
        flash("You have already submitted a comment from this IP address.")
        return redirect(url_for("home"))

    content = request.form.get('comentario')
    if not content or len(content) > MAX_COMMENT_LENGTH:
        flash(f"Your comment is either empty or too long (max {MAX_COMMENT_LENGTH} characters).")
        return redirect(url_for("home"))

    db.execute('INSERT INTO comments (content, ip_address, votes, country_code) VALUES (?, ?, ?, ?)',
               (content, ip_address, 0, country_code))
    db.commit()
    flash("Your comment has been submitted successfully!")
    
    total_comments = db.execute('SELECT COUNT(*) FROM comments').fetchone()[0]
    last_page = math.ceil(total_comments / PER_PAGE)
    return redirect(url_for("home", page=last_page))

@app.route("/comentar_ajax", methods=["POST"])
def comentar_ajax():
    ip_address = get_real_ip()
    country_code = get_country_code(ip_address)
    db = get_db()
    existing_comment = db.execute('SELECT id FROM comments WHERE ip_address = ?', (ip_address,)).fetchone()
    if existing_comment:
        return jsonify({"success": False, "message": "You have already submitted a comment from this IP address."})
    content = request.form.get('comentario')
    if not content or len(content) > MAX_COMMENT_LENGTH:
        return jsonify({"success": False, "message": f"Your comment is either empty or too long (max {MAX_COMMENT_LENGTH} characters)."})
    db.execute('INSERT INTO comments (content, ip_address, votes, country_code) VALUES (?, ?, ?, ?)', (content, ip_address, 0, country_code))
    db.commit()

    total_comments = db.execute('SELECT COUNT(*) FROM comments').fetchone()[0]
    last_page = math.ceil(total_comments / PER_PAGE)
    
    comment = db.execute(
        'SELECT id, content, votes, country_code FROM comments WHERE ip_address = ? ORDER BY id DESC LIMIT 1',
        (ip_address,)
    ).fetchone()

    return jsonify({
        "success": True,
        "message": "Your comment has been submitted successfully!",
        "last_page": last_page,
        "comment": {
            "id": comment["id"],
            "content": comment["content"],
            "votes": comment["votes"],
            "country_code": comment["country_code"],
            "emoji": country_code_to_emoji(comment["country_code"])
        }
    })

@app.route("/upvote/<int:comment_id>", methods=["POST"])
def upvote(comment_id):
    ip_address = get_real_ip()
    db = get_db()
    
    already_upvoted = db.execute(
        'SELECT id FROM upvotes WHERE comment_id = ? AND ip_address = ?',
        (comment_id, ip_address)
    ).fetchone()
    
    if already_upvoted:
        flash("You have already upvoted this comment.")
        return redirect(url_for("home"))

    db.execute('INSERT INTO upvotes (comment_id, ip_address) VALUES (?, ?)', (comment_id, ip_address))
    db.execute('UPDATE comments SET votes = votes + 1 WHERE id = ?', (comment_id,))
    db.commit()

    return redirect(url_for("home"))

@app.route("/upvote_ajax/<int:comment_id>", methods=["POST"])
def upvote_ajax(comment_id):
    ip_address = get_real_ip()
    db = get_db()
    already_upvoted = db.execute(
        'SELECT id FROM upvotes WHERE comment_id = ? AND ip_address = ?',
        (comment_id, ip_address)
    ).fetchone()
    if already_upvoted:
        return jsonify({"success": False, "message": "You have already upvoted this comment."})
    db.execute('INSERT INTO upvotes (comment_id, ip_address) VALUES (?, ?)', (comment_id, ip_address))
    db.execute('UPDATE comments SET votes = votes + 1 WHERE id = ?', (comment_id,))
    db.commit()
    comment = db.execute('SELECT votes, country_code FROM comments WHERE id = ?', (comment_id,)).fetchone()
    emoji = country_code_to_emoji(comment["country_code"])
    return jsonify({"success": True, "votes": comment["votes"], "emoji": emoji})

def get_country_code(ip_address):
    print("IP enviada a ipapi:", ip_address)
    if (ip_address.startswith("127.") or
        ip_address.startswith("192.168.") or
        ip_address.startswith("10.") or
        ip_address.startswith("172.")):
        return "🏳️"  
    try:
        response = requests.get(f"https://ipapi.co/{ip_address}/country/", timeout=2)
        if response.status_code == 200:
            code = response.text.strip()
            if code and len(code) == 2:
                return code.upper()
    except Exception as e:
        print("Error ipapi:", e)
    return "KP"

def country_code_to_emoji(code):
    if not code or len(code) != 2:
        return "🏳️" 
    return chr(0x1F1E6 + ord(code[0].upper()) - ord('A')) + chr(0x1F1E6 + ord(code[1].upper()) - ord('A'))

def get_real_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', None)
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)