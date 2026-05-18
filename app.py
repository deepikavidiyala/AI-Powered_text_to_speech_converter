import pyttsx3
from PyPDF2 import PdfReader
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from datetime import datetime
import os

# ---------------- APP ---------------- #

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# ---------------- DATABASE ---------------- #

db = SQLAlchemy(app)

# ---------------- LOGIN MANAGER ---------------- #

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'

# ---------------- AUDIO FOLDER ---------------- #

AUDIO_FOLDER = 'static/audio'

os.makedirs(AUDIO_FOLDER, exist_ok=True)

# ---------------- MODELS ---------------- #

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )


class SpeechHistory(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100)
    )

    text = db.Column(
        db.Text
    )

    language = db.Column(
        db.String(20)
    )

    filename = db.Column(
        db.String(200)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# ---------------- USER LOADER ---------------- #

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

# ---------------- HOME ---------------- #

@app.route('/')
def home():

    return render_template('index.html')

# ---------------- REGISTER ---------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash('Username already exists')

            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)

        db.session.commit()

        flash('Registration Successful')

        return redirect(url_for('login'))

    return render_template('register.html')

# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            return redirect(url_for('dashboard'))

        else:

            flash('Invalid Username or Password')

    return render_template('login.html')

# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard', methods=['GET', 'POST'])

@login_required

def dashboard():

    audio_file = None

    if request.method == 'POST':

        language = request.form['language']

        text = ""

        # ---------------- TEXT INPUT ---------------- #

        if request.form.get('text') and request.form['text'].strip() != "":

            text = request.form['text']

        # ---------------- PDF INPUT ---------------- #

        if 'pdf_file' in request.files:

            pdf = request.files['pdf_file']

            if pdf and pdf.filename != "":

                os.makedirs(
                    'static/uploads',
                    exist_ok=True
                )

                pdf_path = os.path.join(
                    'static/uploads',
                    pdf.filename
                )

                pdf.save(pdf_path)

                reader = PdfReader(pdf_path)

                for page in reader.pages:

                    extracted = page.extract_text()

                    if extracted:


                        print(extracted)

                        text += extracted

        # ---------------- GENERATE SPEECH ---------------- #

        if text.strip() != "":

            filename = f"speech_{datetime.now().timestamp()}.mp3"

            filepath = os.path.join(
                AUDIO_FOLDER,
                filename
            )

            # ---------------- AI VOICE ENGINE ---------------- #

            speed = request.form['speed']

            voice_type = request.form['voice']

            engine = pyttsx3.init()

            # SPEED

            engine.setProperty(
                'rate',
                int(speed)
            )

            # VOICE

            voices = engine.getProperty('voices')

            if voice_type == "female":

                engine.setProperty(
                    'voice',
                    voices[1].id
                )

            else:

                engine.setProperty(
                    'voice',
                    voices[0].id
                )

            # SAVE AUDIO

            engine.save_to_file(
                text,
                filepath
            )

            engine.runAndWait()

            audio_file = filename

            # SAVE HISTORY

            history = SpeechHistory(

                username=current_user.username,

                text=text[:500],

                language=language,

                filename=filename

            )

            db.session.add(history)

            db.session.commit()

    # ---------------- FETCH HISTORY ---------------- #

    history_data = SpeechHistory.query.filter_by(
        username=current_user.username
    ).order_by(
        SpeechHistory.created_at.desc()
    ).all()

    return render_template(

        'dashboard.html',

        audio_file=audio_file,

        username=current_user.username,

        history_data=history_data
    )

    
# ---------------- LOGOUT ---------------- #

@app.route('/logout')

@login_required

def logout():

    logout_user()

    return redirect(url_for('home'))

# ---------------- MAIN ---------------- #

if __name__ == '__main__':

    with app.app_context():

        db.create_all()

    app.run(debug=True)

