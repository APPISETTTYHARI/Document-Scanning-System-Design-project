# app.py
from flask import Flask, request, session, render_template, jsonify, redirect, url_for
import sqlite3
import hashlib
import datetime
import os
from difflib import SequenceMatcher

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, credits INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS documents 
                 (id INTEGER PRIMARY KEY, user_id INTEGER, filename TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS credit_requests 
                 (id INTEGER PRIMARY KEY, user_id INTEGER, status TEXT)''')
    conn.commit()
    conn.close()

# Reset credits daily
def reset_credits():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits = 20")
    conn.commit()
    conn.close()

# Check and reset credits if new day
def check_credit_reset():
    today = datetime.datetime.now().date()
    if not os.path.exists('last_reset.txt'):
        reset_credits()
        with open('last_reset.txt', 'w') as f:
            f.write(str(today))
    else:
        with open('last_reset.txt', 'r') as f:
            last_reset = datetime.datetime.strptime(f.read(), '%Y-%m-%d').date()
        if today > last_reset:
            reset_credits()
            with open('last_reset.txt', 'w') as f:
                f.write(str(today))

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    return render_template('login.html')

@app.route('/auth/register', methods=['POST'])
def register():
    username = request.form['username']
    password = hashlib.sha256(request.form['password'].encode()).hexdigest()
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role, credits) VALUES (?, ?, ?, ?)",
                 (username, password, 'user', 20))
        conn.commit()
        return jsonify({'message': 'Registration successful'}), 200
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username already exists'}), 400
    finally:
        conn.close()

@app.route('/auth/login', methods=['POST'])
def login():
    check_credit_reset()
    username = request.form['username']
    password = hashlib.sha256(request.form['password'].encode()).hexdigest()
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        session['user_id'] = user[0]
        session['role'] = user[3]
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/user/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT username, credits FROM users WHERE id = ?", (session['user_id'],))
    user = c.fetchone()
    c.execute("SELECT id, filename FROM documents WHERE user_id = ?", (session['user_id'],))
    scans = c.fetchall()
    conn.close()
    return render_template('profile.html', username=user[0], credits=user[1], scans=scans)

@app.route('/scan', methods=['POST'])
def scan():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE id = ?", (session['user_id'],))
    credits = c.fetchone()[0]
    if credits < 1:
        conn.close()
        return jsonify({'message': 'Insufficient credits'}), 400
    
    file = request.files['file']
    content = file.read().decode('utf-8')
    filename = file.filename
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    c.execute("INSERT INTO documents (user_id, filename, content) VALUES (?, ?, ?)",
             (session['user_id'], filename, content))
    doc_id = c.lastrowid
    c.execute("UPDATE users SET credits = credits - 1 WHERE id = ?", (session['user_id'],))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Scan successful', 'doc_id': doc_id}), 200

@app.route('/matches/<doc_id>')
def get_matches(doc_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT content FROM documents WHERE id = ?", (doc_id,))
    source_content = c.fetchone()[0]
    c.execute("SELECT id, filename, content FROM documents WHERE id != ?", (doc_id,))
    all_docs = c.fetchall()
    conn.close()
    
    matches = []
    for doc in all_docs:
        similarity = SequenceMatcher(None, source_content, doc[2]).ratio()
        if similarity > 0.7:  # Threshold for similarity
            matches.append({'id': doc[0], 'filename': doc[1], 'similarity': similarity})
    
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return jsonify(matches)

@app.route('/credits/request', methods=['POST'])
def request_credits():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO credit_requests (user_id, status) VALUES (?, ?)",
             (session['user_id'], 'pending'))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Credit request submitted'}), 200

@app.route('/admin/analytics')
def analytics():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT username, credits, (SELECT COUNT(*) FROM documents WHERE user_id = users.id) as scans FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('analytics.html', users=users)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    init_db()
    app.run(debug=True)