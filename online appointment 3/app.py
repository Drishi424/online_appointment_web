from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'd7ca7dcbb103e83ee8ac817640167373'  # replace with your generated secret key

DOCTOR_FILE = 'data/doctors.json'

# Helpers to load and save JSON
def load_doctors():
    if not os.path.exists(DOCTOR_FILE):
        return []
    with open(DOCTOR_FILE, 'r') as f:
        return json.load(f)

def save_doctors(doctors):
    with open(DOCTOR_FILE, 'w') as f:
        json.dump(doctors, f, indent=4)

# Auto-reject expired offline requests
def auto_reject_expired_requests():
    now = datetime.now()
    doctors = load_doctors()
    for doc in doctors:
        if not doc['is_online']:
            updated_requests = []
            for req in doc.get('pending_requests', []):
                try:
                    req_time = datetime.strptime(req['preferred_time'], '%Y-%m-%dT%H:%M')
                    if now < req_time:
                        updated_requests.append(req)
                except:
                    continue
            doc['pending_requests'] = updated_requests
    save_doctors(doctors)

@app.route('/')
def home():
    auto_reject_expired_requests()
    return render_template('home.html')

@app.route('/doctor')
def doctor_page():
    return render_template('doctor_login.html')

@app.route('/doctor/signup', methods=['GET', 'POST'])
def doctor_signup():
    if request.method == 'POST':
        new_doc = {
            'id': request.form['id'],
            'password': request.form['password'],
            'name': request.form['name'],
            'expertise': request.form['expertise'],
            'experience': request.form['experience'],
            'degree': request.form['degree'],
            'contact': request.form['contact'],
            'is_online': False,
            'token_counter': 0,
            'accepted_appointments': [],
            'pending_requests': []
        }
        doctors = load_doctors()
        doctors.append(new_doc)
        save_doctors(doctors)
        return redirect(url_for('doctor_page'))
    return render_template('doctor_signup.html')

@app.route('/doctor/login', methods=['POST'])
def doctor_login():
    doc_id = request.form['id']
    password = request.form['password']
    doctors = load_doctors()
    for doc in doctors:
        if doc['id'] == doc_id and doc['password'] == password:
            session['doctor_id'] = doc_id
            return redirect(url_for('doctor_dashboard'))
    flash('Invalid credentials')
    return redirect(url_for('doctor_page'))

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_page'))
    doc_id = session['doctor_id']
    doctors = load_doctors()
    doctor = next((d for d in doctors if d['id'] == doc_id), None)
    return render_template('doctor_dashboard.html', doctor=doctor)

@app.route('/doctor/toggle_status')
def toggle_status():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_page'))
    doc_id = session['doctor_id']
    doctors = load_doctors()
    for doc in doctors:
        if doc['id'] == doc_id:
            doc['is_online'] = not doc['is_online']
            break
    save_doctors(doctors)
    return redirect(url_for('doctor_dashboard'))

@app.route('/patients')
def patient_view():
    doctors = load_doctors()
    return render_template('patient_view.html', doctors=doctors)

@app.route('/book/<doc_id>', methods=['POST'])
def book_appointment(doc_id):
    patient_name = request.form['username']
    phone = request.form['phone']
    preferred_time = request.form['preferred_time']
    doctors = load_doctors()
    for doc in doctors:
        if doc['id'] == doc_id:
            if doc['is_online']:
                doc['token_counter'] += 1
                doc['accepted_appointments'].append({
                    'name': patient_name,
                    'phone': phone,
                    'token': doc['token_counter']
                })
                flash(f"Appointment confirmed! Your token is #{doc['token_counter']}")
            else:
                if 'pending_requests' not in doc:
                    doc['pending_requests'] = []
                doc['pending_requests'].append({
                    'name': patient_name,
                    'phone': phone,
                    'preferred_time': preferred_time
                })
                flash("Doctor is offline. Your request has been sent with preferred time.")
            break
    save_doctors(doctors)
    return redirect(url_for('patient_view'))

@app.route('/accept_request/<int:req_index>')
def accept_request(req_index):
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_page'))
    doc_id = session['doctor_id']
    doctors = load_doctors()
    for doc in doctors:
        if doc['id'] == doc_id:
            req = doc['pending_requests'].pop(req_index)
            doc['token_counter'] += 1
            doc['accepted_appointments'].append({
                'name': req['name'],
                'phone': req['phone'],
                'token': doc['token_counter']
            })
            break
    save_doctors(doctors)
    return redirect(url_for('doctor_dashboard'))

@app.route('/reject_request/<int:req_index>')
def reject_request(req_index):
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_page'))
    doc_id = session['doctor_id']
    doctors = load_doctors()
    for doc in doctors:
        if doc['id'] == doc_id:
            doc['pending_requests'].pop(req_index)
            break
    save_doctors(doctors)
    return redirect(url_for('doctor_dashboard'))

@app.route('/attended/<int:token>')
def mark_attended(token):
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_page'))
    doc_id = session['doctor_id']
    doctors = load_doctors()
    for doc in doctors:
        if doc['id'] == doc_id:
            doc['accepted_appointments'] = [a for a in doc['accepted_appointments'] if a['token'] != token]
            break
    save_doctors(doctors)
    return redirect(url_for('doctor_dashboard'))

@app.route('/logout')
def logout():
    session.pop('doctor_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
