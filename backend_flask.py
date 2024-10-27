# Install required packages
# pip install Flask Flask-SQLAlchemy google-cloud-storage

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from google.cloud import storage
import os
import base64
import time
import os
from google.cloud import storage

# Set the environment variable to the path of your service account key file
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'model-city-connect-three-2b393930c5c6.json'  # Change to your path

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 'image_submissions_model_city'  # Replace with your actual bucket name
bucket = storage_client.bucket(bucket_name)

app = Flask(__name__)

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'  
db = SQLAlchemy(app)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    winner = db.Column(db.String(10), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)

@app.route('/')
def index():
    return render_template('scoreboard.html')  # This serves the index.html file

@app.route('/api/scores', methods=['GET'])
def get_scores():
    east_score = Score.query.filter_by(winner='east').count()
    west_score = Score.query.filter_by(winner='west').count()
    return jsonify({'east': east_score, 'west': west_score})

@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    data = request.json
    winner = data['winner']
    image_data = data['image'].split(',')[1]  # Remove the "data:image/jpeg;base64," part

    # Upload image to Google Cloud Storage
    blob = bucket.blob(f'connect_three_{winner}_{int(time.time())}.jpg')
    blob.upload_from_string(base64.b64decode(image_data), content_type='image/jpeg')

    # Create public URL
    blob.make_public()
    image_url = blob.public_url

    # Save score to database
    new_score = Score(winner=winner, image_url=image_url)
    db.session.add(new_score)
    db.session.commit()

    return jsonify({'message': 'Score submitted successfully'}), 200

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback = db.Column(db.Text, nullable=True)
    stress_before = db.Column(db.Integer, nullable=False)
    stress_after = db.Column(db.Integer, nullable=False)

@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    stress_before = data['stress_before']
    stress_after = data['stress_after']
    feedback = data.get('feedback', '')  # Optional feedback

    # Save feedback to database
    new_response = Feedback(stress_before=stress_before, stress_after=stress_after,feedback=feedback)
    db.session.add(new_response)
    db.session.commit()

    return jsonify({'message': 'Feedback submitted successfully'}), 200

@app.route('/api/feedback', methods=['GET'])
def view_feedback():
    feedbacks = Feedback.query.all()
    return jsonify([{
        'id': f.id, 
        'feedback': f.feedback,
        'stress_before': f.stress_before,
        'stress_after': f.stress_after
    } for f in feedbacks])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)