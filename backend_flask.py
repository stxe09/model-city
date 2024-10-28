# Install required packages
# pip install Flask Flask-SQLAlchemy google-cloud-storage

from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from google.cloud import storage
import json
import base64
import time
from datetime import datetime
import os
from google.cloud import storage
from datetime import datetime

# Set the environment variable to the path of your service account key file
# MUST comment out before deploying to Heroku
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'model-city-connect-three-2b393930c5c6.json'  # Change to your path

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 'image_submissions_model_city'  # Replace with your actual bucket name
bucket = storage_client.bucket(bucket_name)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.dbbb'  
dbbb = SQLAlchemy(app)

class Score(dbbb.Model):
    id = dbbb.Column(dbbb.Integer, primary_key=True)
    winner = dbbb.Column(dbbb.String(10), nullable=False)
    image_url = dbbb.Column(dbbb.String(200), nullable=False)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST')
    if response.mimetype == 'text/event-stream':
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/score-updates')
def score_updates():
    def generate():
        with app.app_context():
            while True:
                try:
                    # Get current scores within the application context
                    east_score = Score.query.filter_by(winner='east').count()
                    west_score = Score.query.filter_by(winner='west').count()
                    
                    # Format the SSE data
                    data = json.dumps({
                        'east': east_score,
                        'west': west_score,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    yield f"data: {data}\n\n"
                    time.sleep(2)  # Update every 2 seconds
                except Exception as e:
                    print(f"Error in SSE stream: {str(e)}")
                    yield f"event: error\ndata: {str(e)}\n\n"
                    time.sleep(2)  # Wait before retrying
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/')
def index():
    return render_template('scoreboard.html')

@app.route('/api/scores', methods=['GET'])
def get_scores():
    east_score = Score.query.filter_by(winner='east').count()
    west_score = Score.query.filter_by(winner='west').count()
    return jsonify({'east': east_score, 'west': west_score})

@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    data = request.json
    winner = data['winner']
    if data['image']:
        image_data = data['image'].split(',')[1]
        # Upload image to Google Cloud Storage
        blob = bucket.blob(f'connect_three_{winner}_{int(time.time())}.jpg')
        blob.upload_from_string(base64.b64decode(image_data), content_type='image/jpeg')

        # Create public URL
        blob.make_public()
        image_url = blob.public_url

    else: 
        image_data = "none"
    
    # Save score to database
    new_score = Score(winner=winner, image_url=image_url)
    dbbb.session.add(new_score)
    dbbb.session.commit()

    return jsonify({'message': 'Score submitted successfully'}), 200

# TODO: Jiawei to change model after Samuel confirms questions. Please test it and make sure we can access responses at host.com/api/feedback
class Feedback(dbbb.Model):
    id = dbbb.Column(dbbb.Integer, primary_key=True)
    # time_of_response = dbbb.Column(dbbb.DateTime) # Want to add this so that 
    date = dbbb.Column(dbbb.DateTime, default=datetime.utcnow)
    group = dbbb.Column(dbbb.String(20), nullable=False)
    gender = dbbb.Column(dbbb.String(20), nullable=False)
    category = dbbb.Column(dbbb.String(20), nullable=False)
    before = dbbb.Column(dbbb.String(20), nullable=False)
    again = dbbb.Column(dbbb.String(20), nullable=False)
    stress_before = dbbb.Column(dbbb.Integer, nullable=False)
    stress_after = dbbb.Column(dbbb.Integer, nullable=False)
    play = dbbb.Column(dbbb.Integer, nullable=False)
    competition = dbbb.Column(dbbb.Integer, nullable=False)
    region = dbbb.Column(dbbb.Integer, nullable=False)
    sticker = dbbb.Column(dbbb.Integer, nullable=False)
    space = dbbb.Column(dbbb.Integer, nullable=False)
    more = dbbb.Column(dbbb.Text, nullable=False)
    feedback = dbbb.Column(dbbb.Text, nullable=True)
    
@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    group = data.get('group')  # No KeyError, returns None if missing
    gender = data.get('gender')
    category = data.get('category')
    before = data.get('before')
    again = data.get('again')
    stress_before = data.get('stress_before')
    stress_after = data.get('stress_after')
    play = data.get('play')
    competition = data.get('competition')
    region = data.get('region')
    sticker = data.get('sticker')
    space = data.get('space')
    more = data.get('more')
    feedback = data.get('feedback', '')  # Optional feedback

    # Save feedback to database
    new_response = Feedback(
        group = group,
        gender = gender,
        category = category,
        before = before,
        again = again,
        stress_before=stress_before, 
        stress_after=stress_after,
        play = play,
        competition = competition,
        region = region,
        sticker = sticker,
        space = space,
        more = more,
        feedback=feedback)
    dbbb.session.add(new_response)
    dbbb.session.commit()

    return jsonify({'message': 'Feedback submitted successfully'}), 200

@app.route('/api/feedback', methods=['GET'])
def view_feedback():
    feedbacks = Feedback.query.all()
    return jsonify([{
        'id': f.id,
        'date': f.date.isoformat(),
        'group': f.group,
        'gender': f.gender,
        'category': f.category, 
        'before': f.before,
        'again': f.again,
        'stress_before': f.stress_before,
        'stress_after': f.stress_after,
        'play': f.play,
        'competition': f.competition,
        'region': f.region,
        'sticker': f.sticker,
        'space': f.space,
        'more': f.more,
        'feedback': f.feedback,
    } for f in feedbacks])

"""
To access the admin panel:

Press Ctrl + Shift + K to show/hide the admin panel
Enter your admin key in the password field: model-city-reset-scores
Click "Reset All Scores" to reset the scores
Confirm the reset when prompted
"""
@app.route('/api/reset-scores', methods=['POST'])
def reset_scores():
    # Add a secret key check for security
    if request.headers.get('X-Admin-Key') != 'model-city-reset-scores':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Delete all scores from the database
        Score.query.delete()
        dbbb.session.commit()
        return jsonify({'message': 'Scores reset successfully'}), 200
    except Exception as e:
        dbbb.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add this function to help recover if needed
@app.route('/api/scores/count', methods=['GET'])
def get_score_count():
    try:
        count = Score.query.count()
        return jsonify({'total_scores': count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

if __name__ == '__main__':
    with app.app_context():
        dbbb.create_all()  # Create database tables
    app.run(debug=True, threaded = True)