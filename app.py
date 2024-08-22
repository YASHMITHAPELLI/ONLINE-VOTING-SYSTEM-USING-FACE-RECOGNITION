import json
import re
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for, render_template_string
import requests
import mysql.connector
import cv2
import os
#from sklearn.neighbors import KNeighborsClassifier
# import pandas as pd
# import joblib
import numpy as np

app = Flask(__name__)
app.secret_key = 'bc6125d05905005b6cdf54414aa3d687'

app.static_folder = 'static'
nimgs = 50
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
aadhar_verified = False
def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []
# def train_model():
#     faces = []
#     labels = []
#     userlist = os.listdir('static/faces')
#     for user in userlist:
#         for imgname in os.listdir(f'static/faces/{user}'):
#             img = cv2.imread(f'static/faces/{user}/{imgname}')
#             resized_face = cv2.resize(img, (50, 50))
#             faces.append(resized_face.ravel())
#             labels.append(user)
#     faces = np.array(faces)
#     knn = KNeighborsClassifier(n_neighbors=5)
#     knn.fit(faces, labels)
#     joblib.dump(knn, 'D:/DOWNLOADS/socvotealmost/socvote/flaskphp/models/face_recognition_model.pkl')

# Replace these with your actual database credentials
db_config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': 'root',
    'database': 'kahipn'
}

# Create a connection to the database
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()


@app.route('/')
def index():
    return render_template('loginpage.html')


@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')


@app.route('/contactus')
def contactus():
    return render_template('contactus.html')


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            if not username[0].isalpha():
                flash("Username should not start with a number", "error")
                return redirect(url_for('index'))
            if username != "root" or password != "root":
                flash("Invalid username or password", "error")
                return redirect(url_for('index'))
            return render_template('registration.html')
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for('index'))


@app.route('/process_registration', methods=['GET', 'POST'])
def process_registration():
    global aadhar_verified
    cursor = None  # Initialize the cursor outside the try block
    try:
        name = request.form['name']
        flat_number = request.form['flatNumber']
        aadhar_id = request.form.get('aadhar')
        voter_id = request.form['voterID']
        radio_option = request.form.get('option')

        # if not aadhar_verified:
        #     flash('Please verify Aadhar first.', 'error')
        #     alert_message = "<script>alert('Aadhar verification failed. Please verify Aadhar first.');</script>"
        #     return render_template('registration.html')
        # Perform validations
        if not name or not flat_number or not aadhar_id or not voter_id or not radio_option:
            flash('All fields are required.', 'error')
            return render_template('registration.html', name=name, flat_number=flat_number, aadhar_id=aadhar_id,
                                   voter_id=voter_id, radio_option=radio_option)

        # Validate name (for example, ensure it doesn't start with a number)
        if not name[0].isalpha():
            flash('Name should not start with a number.', 'error')
            return render_template('registration.html', name=name, flat_number=flat_number, aadhar_id=aadhar_id,
                                   voter_id=voter_id, radio_option=radio_option)

        # Validate flat number format (for example, ensure it has a specific format)
        if not re.match(r'^[A-Za-z]\d{3}$', flat_number):
            flash('Flat number should start with an alphabet followed by three digits (e.g., B102).', 'error')
            return render_template('registration.html', name=name, flat_number=flat_number, aadhar_id=aadhar_id,
                                   voter_id=voter_id, radio_option=radio_option)

        # Validate Aadhar number format (for example, ensure it has a specific format)
        if not re.match(r'^\d{12}$', aadhar_id):
            flash('Aadhar number should be a 12-digit number.', 'error')
            return render_template('registration.html', name=name, flat_number=flat_number, aadhar_id=aadhar_id,
                                   voter_id=voter_id, radio_option=radio_option)

        # Validate radio button option
        if radio_option not in ['Voter', 'Candidate']:
            flash('Please select one of the options.', 'error')
            return render_template('registration.html', name=name, flat_number=flat_number, aadhar_id=aadhar_id,
                                   voter_id=voter_id, radio_option=radio_option)

        userimagefolder = 'static/Headshots/'+name+'_'+str(flat_number)
        if not os.path.isdir(userimagefolder):
            os.makedirs(userimagefolder)
        i, j = 0, 0
        cap = cv2.VideoCapture(0)
        while 1:
                _, frame = cap.read()
                faces = extract_faces(frame)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
                    cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
                    if j % 5 == 0:
                        username = name+'_'+str(i)+'.jpg'
                        cv2.imwrite(userimagefolder+'/'+username, frame[y:y+h, x:x+w])
                        i += 1
                    j += 1
                if j == nimgs*5:
                    break
                cv2.imshow('Adding new User', frame)
                if cv2.waitKey(1) == 27:
                    break
        cap.release()
        cv2.destroyAllWindows()
        print('Training Model')
        # train_model() 
        if not conn.is_connected():
            conn.connect()
        # Reconnect the cursor
        cursor = conn.cursor()
        radio_option = request.form.get('option')
        if radio_option == 'Voter':
            sql = """INSERT INTO voter(name, aadhar_no, voter_id_card, flat_no)
                 VALUES (%s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE 
                 name = VALUES(name), aadhar_no = VALUES(aadhar_no), 
                 voter_id_card = VALUES(voter_id_card), flat_no = VALUES(flat_no)
                """
            cursor.execute(sql, (name, aadhar_id, voter_id, flat_number))
        elif radio_option == 'Candidate':
            sql = """INSERT INTO voter(name, aadhar_no, voter_id_card, flat_no)
                 VALUES (%s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE 
                 name = VALUES(name), aadhar_no = VALUES(aadhar_no), 
                 voter_id_card = VALUES(voter_id_card), flat_no = VALUES(flat_no)
                """
            sqll = """INSERT INTO candidate(name, aadhar_no, voter_id_card, flat_no)
                 VALUES (%s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE 
                 name = VALUES(name), aadhar_no = VALUES(aadhar_no), 
                 voter_id_card = VALUES(voter_id_card), flat_no = VALUES(flat_no)
                """
            cursor.execute(sql, (name, aadhar_id, voter_id, flat_number))
            cursor.execute(sqll, (name, aadhar_id, voter_id, flat_number))
        conn.commit()
        # return jsonify({'success': True})
        flash('Form submitted successfully!', 'success')
        return render_template('registration.html')

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash(f"Error: {err}", 'error')
        return render_template('registration.html')


@app.route('/send_otp', methods=['POST'])
def send_otp():
    aadhar_no = request.form.get('aadhar_no')
    # Implement your logic to send OTP and return a response
    url = 'https://api.sandbox.co.in/kyc/aadhaar/okyc/otp'
    payload = {"aadhaar_number": aadhar_no}
    headers = {
        'Authorization': 'eyJhbGciOiJIUzUxMiJ9.eyJhdWQiOiJBUEkiLCJyZWZyZXNoX3Rva2VuIjoiZXlKaGJHY2lPaUpJVXpVeE1pSjkuZXlKaGRXUWlPaUpCVUVraUxDSnpkV0lpT2lKNVlYTm9iV2wwYUdGd1pXeHNhVEV5TXpRMU5qYzRPVUJuYldGcGJDNWpiMjBpTENKaGNHbGZhMlY1SWpvaWEyVjVYMnhwZG1WZldHNXdTazVDVmpNd2VFUlRTRnBzY1U4MFZFOXFOWFl5VVRkYU5EazVVVTBpTENKcGMzTWlPaUpoY0drdWMyRnVaR0p2ZUM1amJ5NXBiaUlzSW1WNGNDSTZNVGMwTXpZM05ERXdOaXdpYVc1MFpXNTBJam9pVWtWR1VrVlRTRjlVVDB0RlRpSXNJbWxoZENJNk1UY3hNakV6T0RFd05uMC5adDczZHgwUGJFaGpfMlNhSXVwaFFEaUxfa3p6UDNoU0JzZkhOMXNxYWRIMUtsTW9OaTh0OUpuREJna2xSdFVkemI0Y09xZ2xVeHFFaWRjQUdSN004USIsInN1YiI6Inlhc2htaXRoYXBlbGxpMTIzNDU2Nzg5QGdtYWlsLmNvbSIsImFwaV9rZXkiOiJrZXlfbGl2ZV9YbnBKTkJWMzB4RFNIWmxxTzRUT2o1djJRN1o0OTlRTSIsImlzcyI6ImFwaS5zYW5kYm94LmNvLmluIiwiZXhwIjoxNzEyMjI0NTA2LCJpbnRlbnQiOiJBQ0NFU1NfVE9LRU4iLCJpYXQiOjE3MTIxMzgxMDZ9.rSPUFRisuA3bom7qGA7LTEiFqcpBMnEA6z1XQBgEJljJNPC0dvuvThn4DkwoYN3S4Ag0khXQBKkRw2vsU93bWw',
        'content-type': 'application/json',
        'x-api-key': 'key_live_XnpJNBV30xDSHZlqO4TOj5v2Q7Z499QM',
        'x-api-version': '1.0'
    }

    res = requests.post(url, json=payload, headers=headers)
    print(res.text)
    data = res.json()
    return jsonify(data)

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    global aadhar_verified
    otp = request.form.get('otp')
    ref_id = request.form.get('ref_id')
    url = "https://api.sandbox.co.in/kyc/aadhaar/okyc/otp/verify"

    payload = {
        "otp": otp,
        "ref_id": ref_id
    }
    headers = {
        "accept": "application/json",
        "Authorization": 'eyJhbGciOiJIUzUxMiJ9.eyJhdWQiOiJBUEkiLCJyZWZyZXNoX3Rva2VuIjoiZXlKaGJHY2lPaUpJVXpVeE1pSjkuZXlKaGRXUWlPaUpCVUVraUxDSnpkV0lpT2lKNVlYTm9iV2wwYUdGd1pXeHNhVEV5TXpRMU5qYzRPVUJuYldGcGJDNWpiMjBpTENKaGNHbGZhMlY1SWpvaWEyVjVYMnhwZG1WZldHNXdTazVDVmpNd2VFUlRTRnBzY1U4MFZFOXFOWFl5VVRkYU5EazVVVTBpTENKcGMzTWlPaUpoY0drdWMyRnVaR0p2ZUM1amJ5NXBiaUlzSW1WNGNDSTZNVGMwTXpZM05ERXdOaXdpYVc1MFpXNTBJam9pVWtWR1VrVlRTRjlVVDB0RlRpSXNJbWxoZENJNk1UY3hNakV6T0RFd05uMC5adDczZHgwUGJFaGpfMlNhSXVwaFFEaUxfa3p6UDNoU0JzZkhOMXNxYWRIMUtsTW9OaTh0OUpuREJna2xSdFVkemI0Y09xZ2xVeHFFaWRjQUdSN004USIsInN1YiI6Inlhc2htaXRoYXBlbGxpMTIzNDU2Nzg5QGdtYWlsLmNvbSIsImFwaV9rZXkiOiJrZXlfbGl2ZV9YbnBKTkJWMzB4RFNIWmxxTzRUT2o1djJRN1o0OTlRTSIsImlzcyI6ImFwaS5zYW5kYm94LmNvLmluIiwiZXhwIjoxNzEyMjI0NTA2LCJpbnRlbnQiOiJBQ0NFU1NfVE9LRU4iLCJpYXQiOjE3MTIxMzgxMDZ9.rSPUFRisuA3bom7qGA7LTEiFqcpBMnEA6z1XQBgEJljJNPC0dvuvThn4DkwoYN3S4Ag0khXQBKkRw2vsU93bWw',
        "x-api-key": "key_live_XnpJNBV30xDSHZlqO4TOj5v2Q7Z499QM",
        "x-api-version": "1.0",
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    res = json.loads(response.text)
    print(res["code"])
    if res["code"] == 200:
        aadhar_verified = True

    print(response.text)
    return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True)