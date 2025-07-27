import os
import uuid
import time
import numpy as np
import cv2
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from tensorflow.keras.models import load_model

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///deepfake.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

MODEL_PATH = 'deepfake_model.h5'
model = load_model(MODEL_PATH)

# ------------------ Database Models ------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(300))
    label = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    created_at = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ Routes ------------------
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Email already registered")
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        user = User(email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file uploaded'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    filename = str(uuid.uuid4()) + "_" + file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        start = time.time()
        cap = cv2.VideoCapture(filepath)
        frames = []
        max_frames = 30
        while len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (128, 128))
            frame = frame / 255.0
            frames.append(frame)
        cap.release()

        if not frames:
            return jsonify({'error': 'No frames extracted'}), 400

        # सिर्फ पहला फ्रेम ले रहे हैं
        frame = np.expand_dims(frames[0], axis=0)
        prediction = model.predict(frame)
        print("Prediction raw output:", prediction)

        # Softmax vs Sigmoid handle
        if prediction.shape[1] == 2:
            label_idx = np.argmax(prediction[0])
            label = 'REAL' if label_idx == 1 else 'FAKE'
            confidence = float(prediction[0][label_idx])
        else:
            confidence = float(prediction[0][0])
            label = 'REAL' if confidence > 0.5 else 'FAKE'
            confidence = confidence if confidence > 0.5 else 1 - confidence

        end = time.time()

        hist = History(
            user_id=current_user.id,
            filename=file.filename,
            label=label,
            confidence=confidence,
            created_at=time.strftime("%d/%m/%Y, %I:%M:%S %p")
        )
        db.session.add(hist)
        db.session.commit()

        return jsonify({
            'label': label,
            'confidence': confidence,
            'inference_time': round(end - start, 3),
            'model': MODEL_PATH,
            'created_at': hist.created_at,
            'id': hist.id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
@login_required
def api_history():
    records = History.query.filter_by(user_id=current_user.id).order_by(History.id.desc()).all()
    data = [
        {
            'id': r.id,
            'filename': r.filename,
            'label': r.label,
            'confidence': r.confidence,
            'created_at': r.created_at
        } for r in records
    ]
    return jsonify({'history': data})

# ------------------ Main ------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)















