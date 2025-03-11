from flask import Blueprint, request, render_template, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import db, User
import bcrypt
import random
from smtplib import SMTP
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()
auth = Blueprint('auth', __name__)

login_manager = LoginManager()
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_verification_email(gmail, code):
    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "your-actual-gmail@gmail.com")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "your-app-password-here")
    msg = MIMEText(f"Your verification code is: {code}")
    msg["Subject"] = "Handwritten OCR Verification Code"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = gmail
    try:
        with SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, gmail, msg.as_string())
    except Exception as e:
        print(f"Email sending failed: {e}")
        raise

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, verified=True).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            login_user(user)
            return redirect(url_for('main.upload_file'))
        return render_template('login.html', error='Invalid credentials or Gmail not verified!')
    return render_template('login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        gmail = request.form['gmail']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(username=username, password=hashed_password, gmail=gmail)
        try:
            db.session.add(user)
            db.session.commit()
        except:
            db.session.rollback()
            return render_template('signup.html', error='Username or Gmail already exists!')
        verification_code = str(random.randint(1000, 9999))
        session['verification_code'] = verification_code
        session['username'] = username
        send_verification_email(gmail, verification_code)
        return redirect(url_for('auth.verify'))
    return render_template('signup.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        code = request.form['code']
        if code == session.get('verification_code'):
            username = session.get('username')
            user = User.query.filter_by(username=username).first()
            user.verified = True
            db.session.commit()
            login_user(user)
            return redirect(url_for('main.upload_file'))
        return render_template('verify.html', error='Invalid verification code!')
    return render_template('verify.html')