from flask import Flask, render_template, request, redirect, url_for, session, flash
import boto3
import uuid
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# AWS Setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
sns_client = boto3.client('sns', region_name='us-east-1')

# DynamoDB Tables
users_table = dynamodb.Table('Users')
meds_table = dynamodb.Table('Medications')
doctors_table = dynamodb.Table('Doctors')

# SNS Topic ARN
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:YourTopicName'  # <-- Replace with actual ARN

# -------------------- ROUTES --------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login-existing', methods=['POST'])
def login_existing():
    email = request.form['email']
    password = request.form['password']

    response = users_table.get_item(Key={'email': email})
    user = response.get('Item')

    if user and user['password'] == password:
        session['username'] = user['name']
        session['email'] = user['email']
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid email or password", "error")
        return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    # Check if user exists
    if 'Item' in users_table.get_item(Key={'email': email}):
        flash("User already exists. Please login.", "error")
        return render_template('login.html')

    # Add user to DynamoDB
    users_table.put_item(Item={'email': email, 'name': name, 'password': password})

    # Subscribe the user's email to the SNS Topic (if not already subscribed)
    try:
        sns_client.subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol='email',
            Endpoint=email
        )
        flash("A confirmation email has been sent to your email. Please confirm the subscription to receive notifications.", "info")
    except Exception as e:
        print(f"Error subscribing to SNS: {e}")

    # Send a Welcome Email via SNS Topic
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=f"Hello {name},\n\nWelcome to MedTrack!\nYour registration was successful.",
            Subject="Welcome to MedTrack!"
        )
    except Exception as e:
        print(f"Error sending SNS message: {e}")

    flash("Registration successful! Please login.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    username = session['username']

    all_meds = meds_table.scan(
        FilterExpression='user_email = :u',
        ExpressionAttributeValues={':u': email}
    )['Items']

    today = date.today().isoformat()
    reminders = [m for m in all_meds if m['start_date'] <= today <= m['end_date']]

    doctor = doctors_table.get_item(Key={'user_email': email}).get('Item')

    return render_template('dashboard.html', username=username, medications=all_meds,
                           reminders=reminders, doctor=doctor)

@app.route('/add-medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        form = request.form
        meds_table.put_item(Item={
            'id': str(uuid.uuid4()),
            'user_email': session['email'],
            'medicine_name': form['medicine_name'],
            'dose_count': form['dose_count'],
            'dose_time': form['dose_time'],
            'start_date': form['start_date'],
            'end_date': form['end_date'],
            'frequency': form['frequency']
        })
        flash("Medicine added successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_medicine.html')

@app.route('/edit-medicine/<string:medicine_id>', methods=['GET', 'POST'])
def edit_medicine(medicine_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        form = request.form
        meds_table.put_item(Item={
            'id': medicine_id,
            'user_email': session['email'],
            'medicine_name': form['medicine_name'],
            'dose_count': form['dose_count'],
            'dose_time': form['dose_time'],
            'start_date': form['start_date'],
            'end_date': form['end_date'],
            'frequency': form['frequency']
        })
        flash("Medicine updated successfully.", "success")
        return redirect(url_for('dashboard'))

    med = meds_table.get_item(Key={'id': medicine_id}).get('Item')
    if not med or med['user_email'] != session['email']:
        return "Medicine not found or access denied."

    return render_template('edit_medicine.html', medicine=med)

@app.route('/delete-medicine/<string:medicine_id>', methods=['POST'])
def delete_medicine(medicine_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    meds_table.delete_item(Key={'id': medicine_id})
    flash("Medicine deleted.", "info")
    return redirect(url_for('dashboard'))

@app.route('/doctor-info', methods=['GET', 'POST'])
def doctor_info():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']

    if request.method == 'POST':
        form = request.form
        doctors_table.put_item(Item={
            'user_email': email,
            'name': form['name'],
            'specialization': form['specialization'],
            'phone': form['phone'],
            'email': form['email'],
            'next_checkup_date': form['next_checkup_date']
        })
        flash("Doctor info saved.", "success")
        return redirect(url_for('dashboard'))

    doctor = doctors_table.get_item(Key={'user_email': email}).get('Item')
    return render_template('doctor_form.html', doctor=doctor)

@app.route('/user')
def user_profile():
    if 'email' not in session:
        return redirect(url_for('login'))

    return render_template('user_profile.html',
                           username=session.get('username'),
                           email=session.get('email'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# -------------------- MAIN --------------------

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
