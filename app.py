from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import sqlite3
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from vision_api import extract_text
from translate_api import translate_text
from summarize_api import summarize_text
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from oauthlib.oauth2 import WebApplicationClient

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure key
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Google OAuth setup (placeholder)
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"  # Replace with your Google Client ID
client = WebApplicationClient(GOOGLE_CLIENT_ID)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
@login_required
def upload_file():
    if request.method == "POST":
        if "files" not in request.files:
            return "No files uploaded!"

        files = request.files.getlist("files")
        results = []
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                extracted_text = extract_text(filepath)
                formatted_text = ' '.join(extracted_text.split()).replace('. ', '. ')
                results.append({"image": filename, "text": formatted_text})
                c.execute("INSERT INTO history (user_id, image, text) VALUES (?, ?, ?)",
                          (current_user.id, filename, formatted_text))
        conn.commit()
        conn.close()
        return render_template("result.html", results=results)
    return render_template("index.html")

@app.route("/translate", methods=["POST"])
@login_required
def translate():
    text = request.form.get("text")
    target_lang = request.form.get("language")
    translated_text = translate_text(text, target_lang)
    return translated_text

@app.route("/summarize", methods=["POST"])
@login_required
def summarize():
    text = request.form["text"]
    summary = summarize_text(text)
    return summary

@app.route("/download", methods=["POST"])
@login_required
def download():
    text = request.form["text"]
    filename = request.form["filename"]
    format = request.form["format"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], f"{filename}.{format}")
    text = text.replace('<br>', '\n').replace('</p><p>', '\n').replace('<p>', '').replace('</p>', '\n')
    if format == "docx":
        doc = Document()
        doc.add_paragraph(text)
        doc.save(filepath)
    elif format == "pdf":
        pdf = SimpleDocTemplate(filepath, pagesize=letter)
        pdf.build([Paragraph(text)])
    else:  # txt
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(text)
    return send_file(filepath, as_attachment=True)

@app.route("/feedback", methods=["POST"])
def feedback():
    # No database operations, just return a success response
    return jsonify({"success": True, "message": "Thank you, your message has been sent successfully!"})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            login_user(User(user[0]))
            return redirect(url_for("upload_file"))
        return "Invalid credentials!"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        gmail = request.form["gmail"]
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, gmail) VALUES (?, ?, ?)",
                  (username, password, gmail))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        login_user(User(user_id))
        return redirect(url_for("upload_file"))
    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/history")
@login_required
def history():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT image, text, timestamp FROM history WHERE user_id=? ORDER BY timestamp DESC",
              (current_user.id,))
    records = c.fetchall()
    conn.close()
    return render_template("history.html", records=records)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        password = request.form["password"]
        gmail = request.form["gmail"]
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("UPDATE users SET password=?, gmail=? WHERE id=?", (password, gmail, current_user.id))
        conn.commit()
        conn.close()
        return "Settings updated!"
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT username, gmail FROM users WHERE id=?", (current_user.id,))
    user = c.fetchone()
    conn.close()
    return render_template("settings.html", username=user[0], gmail=user[1])

@app.route("/about")
def about():
    team_members = [
        {"name": "Bhuwan Shrestha", "role": "Lead Developer", "image": "bhuwan_shrestha.jpg"},
        {"name": "Alen Varghese", "role": "UI/UX Designer", "image": "alen_varghese.jpg"},
        {"name": "Shubh Soni", "role": "Machine Learning Expert", "image": "shubh_soni.jpg"},
        {"name": "Dev Patel", "role": "Backend Engineer", "image": "dev_patel.jpg"}
    ]
    return render_template("about.html", team_members=team_members)

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)