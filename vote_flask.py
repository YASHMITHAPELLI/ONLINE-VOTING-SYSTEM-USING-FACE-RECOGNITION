from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
import pymysql
import cv2
# import joblib
import numpy as np
import os
# import pandas as pd
from tensorflow.keras.models import load_model
from keras.preprocessing import image
from keras_vggface import utils
import pickle

app = Flask(__name__)
app.secret_key = '1fa8c8da54b54ca8bbcef68a01f93904'

# Database connection parameters
DB_HOST = 'localhost'
DB_PORT = 3307
DB_USER = 'root'  
DB_PASSWORD = ''
DB_NAME = 'data'

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
model = load_model('transfer_learning_trained_face_cnn_model.h5')
connection = None

@app.before_request
def before_request():
    g.connection = pymysql.connect(host=DB_HOST,
                                    port=DB_PORT,
                                    user=DB_USER,
                                    password=DB_PASSWORD,
                                    database=DB_NAME,
                                    cursorclass=pymysql.cursors.DictCursor)

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'connection'):
        g.connection.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    global connection
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        flat_no = request.form['flatNumber']

        # Authenticate user based on username (name) and password (aadhar)
        if authenticate_user(username, password, flat_no):
            session['aadhar_no'] = password
            session['username'] = username
            session['flatNumber'] = flat_no
            if check_vote_status(username):
                return render_template('message.html', message="You have already voted.")
            else:
                return redirect(url_for('voting_page'))
        else:
            return render_template('login.html', message="Invalid username or password.")

    return render_template('login.html', message="")


# Authentication function
def authenticate_user(username, password, flat_no):
    try:
        global connection
        # Connect to the database
        connection = pymysql.connect(host=DB_HOST,
                                     port=DB_PORT,
                                     user=DB_USER,
                                     password=DB_PASSWORD,
                                     database=DB_NAME,
                                     cursorclass=pymysql.cursors.DictCursor)

        with connection.cursor() as cursor:
            # Check if user exists in the database
            cursor.execute("SELECT * FROM voter WHERE name = %s AND aadhar_no = %s AND flat_no = %s", (username, password, flat_no))
            user = cursor.fetchone()

            if user:
                return True
            else:
                return False

    except pymysql.Error as e:
        print("Database error:", e)
        return False

def check_vote_status(username):
    try:
        global connection
        # Connect to the database
        if connection is None:
            return False  # If connection is not established, return False

        with connection.cursor() as cursor:
            # Check the vote_status for the user
            cursor.execute("SELECT vote_status FROM voter WHERE name = %s", username)
            vote_status = cursor.fetchone()['vote_status']

            if vote_status == 1:
                return True
            else:
                return False

    except pymysql.Error as e:
        print("Database error:", e)
        return False

    finally:
        if connection is not None:
            connection.close()


@app.route('/voting_page')
def voting_page():
    try:
        global connection
        # Fetch candidate names from the database
        if connection is None:
            return render_template('error.html', error_message="Database connection error.")

        with g.connection.cursor() as cursor:
            cursor.execute("SELECT cid, name FROM candidate")
            candidates = cursor.fetchall()

    except pymysql.Error as e:
        return render_template('error.html', error_message="Database error: " + str(e))

    return render_template('vote.html', candidates=candidates)

with open("face-labels.pickle", 'rb') as f:
    og_labels = pickle.load(f)
    labels = {key:value for key,value in og_labels.items()}

# resolution of the webcam
screen_width = 640     # try 640 if code fails
screen_height = 720

# size of the image to predict
image_width = 224
image_height = 224

@app.route('/capture_face', methods=['POST'])
def capture_face():
    # Your face recognition logic here
    username = session.get('username')
    flatNumber = session.get('flatNumber')
    newuser = username + '_' + str(flatNumber)

    stream = cv2.VideoCapture(0)

    while True:
        # Capture frame-by-frame
        (grabbed, frame) = stream.read()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # try to detect faces in the webcam
        faces = face_cascade.detectMultiScale(rgb, scaleFactor=1.3, minNeighbors=5)

        # for each face found
        for (x, y, w, h) in faces:
            roi_rgb = rgb[y:y + h, x:x + w]

            # Draw a rectangle around the face
            color = (255, 0, 0)  # in BGR
            stroke = 2
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, stroke)

            # resize the image
            size = (image_width, image_height)
            resized_image = cv2.resize(roi_rgb, size)
            image_array = np.array(resized_image, "uint8")
            img = image_array.reshape(1, image_width, image_height, 3)
            img = img.astype('float32')
            img /= 255

            # predict the image
            predicted_prob = model.predict(img)
            prob_array = np.array(predicted_prob)
            max_value = np.max(prob_array)
            # Display the label
            font = cv2.FONT_HERSHEY_SIMPLEX
            if max_value < 0.97:
                name = 'unknown'
            else:
                name = labels[predicted_prob[0].argmax()]
            color = (255, 0, 255)
            stroke = 2
            cv2.putText(frame, f'({name})', (x, y - 8), font, 1, color, stroke, cv2.LINE_AA)

        # Show the frame
        cv2.imshow("Image", frame)

        # Wait for key press and handle 'q' key to close window
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):  # Press q to break out of the loop
            break

    # Release the camera and close all OpenCV windows
    stream.release()
    cv2.destroyAllWindows()
    print(name)
    # Check if captured face matches the user
    if name == newuser:
        success = True
    else:
        success = False

    return jsonify({"success": success})


@app.route('/vote_handler', methods=['POST'])
def vote_handler():
    if 'selectedCandidate' not in request.form:
        flash("Please select a candidate first.", "error")
        return redirect(url_for('voting_page'))
    selected_candidate = request.form['selectedCandidate']
    aadhar_no = session.get('aadhar_no')

    try:
        # Connect to the database
        # connection = pymysql.connect(host=DB_HOST,
        #                              user=DB_USER,
        #                              password=DB_PASSWORD,
        #                              database=DB_NAME,
        #                              cursorclass=pymysql.cursors.DictCursor)

        with g.connection.cursor() as cursor:
            # Update the votes for the selected candidate
            cursor.execute("UPDATE candidate SET vote = vote + 1 WHERE name = %s", selected_candidate)
            cursor.execute("UPDATE voter SET vote_status = 1 WHERE aadhar_no = %s", (aadhar_no,))
            g.connection.commit()

    except pymysql.Error as e:
        error_message = "Database error: " + str(e)
        return render_template('error.html', error_message=error_message)

    return render_template('message.html', message="Voting successful.")

def fetch_candidates_from_database():
    try:
        # global connection
        # connection = pymysql.connect(host=DB_HOST,
        #                              user=DB_USER,
        #                              password=DB_PASSWORD,
        #                              database=DB_NAME,
        #                              cursorclass=pymysql.cursors.DictCursor)

        with g.connection.cursor() as cursor:
            cursor.execute("SELECT name, vote FROM candidate ORDER BY vote DESC")
            candidates = cursor.fetchall()

        return candidates

    except pymysql.Error as e:
        print("Database error:", e)
        return []


@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/results')
def results():
    candidates = fetch_candidates_from_database()
    return render_template('results.html', candidates=candidates)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

if __name__ == '__main__':
    app.run(debug=True)
