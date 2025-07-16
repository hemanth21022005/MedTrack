from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="8125125637",
    database="medtrack_db"
)
cursor = db.cursor(dictionary=True)

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

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

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

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        flash("User already exists. Please login.", "error")
        return render_template('login.html')

    cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
    db.commit()
    flash("Registration successful! Please login.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    username = session['username']

    cursor.execute("SELECT * FROM medications WHERE user_email = %s", (user_email,))
    all_meds = cursor.fetchall()

    # Show only currently active medications
    today = date.today().isoformat()
    cursor.execute("""
        SELECT * FROM medications
        WHERE user_email = %s AND start_date <= %s AND end_date >= %s
    """, (user_email, today, today))
    todays_meds = cursor.fetchall()

    cursor.execute("SELECT * FROM doctors WHERE user_email = %s", (user_email,))
    doctor = cursor.fetchone()

    return render_template('dashboard.html', username=username, medications=all_meds,
                           reminders=todays_meds, doctor=doctor)

@app.route('/add-medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        form = request.form
        cursor.execute("""
            INSERT INTO medications (user_email, medicine_name, dose_count, dose_time, start_date, end_date, frequency)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session['email'], form['medicine_name'], form['dose_count'], form['dose_time'],
              form['start_date'], form['end_date'], form['frequency']))
        db.commit()
        flash("Medicine added successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_medicine.html')

@app.route('/edit-medicine/<int:medicine_id>', methods=['GET', 'POST'])
def edit_medicine(medicine_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']

    if request.method == 'POST':
        form = request.form
        cursor.execute("""
            UPDATE medications
            SET medicine_name = %s, dose_count = %s, dose_time = %s, start_date = %s, end_date = %s, frequency = %s
            WHERE id = %s AND user_email = %s
        """, (form['medicine_name'], form['dose_count'], form['dose_time'],
              form['start_date'], form['end_date'], form['frequency'], medicine_id, user_email))
        db.commit()
        flash("Medicine updated successfully.", "success")
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM medications WHERE id = %s AND user_email = %s", (medicine_id, user_email))
    medicine = cursor.fetchone()

    if not medicine:
        return "Medicine not found or access denied."

    return render_template('edit_medicine.html', medicine=medicine)

@app.route('/delete-medicine/<int:medicine_id>', methods=['POST'])
def delete_medicine(medicine_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    cursor.execute("DELETE FROM medications WHERE id = %s AND user_email = %s", (medicine_id, user_email))
    db.commit()
    flash("Medicine deleted.", "info")
    return redirect(url_for('dashboard'))

@app.route('/doctor-info', methods=['GET', 'POST'])
def doctor_info():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']

    if request.method == 'POST':
        form = request.form
        cursor.execute("SELECT * FROM doctors WHERE user_email = %s", (user_email,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE doctors
                SET name = %s, specialization = %s, phone = %s, email = %s, next_checkup_date = %s
                WHERE user_email = %s
            """, (form['name'], form['specialization'], form['phone'],
                  form['email'], form['next_checkup_date'], user_email))
        else:
            cursor.execute("""
                INSERT INTO doctors (user_email, name, specialization, phone, email, next_checkup_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_email, form['name'], form['specialization'],
                  form['phone'], form['email'], form['next_checkup_date']))
        db.commit()
        flash("Doctor info saved.", "success")
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM doctors WHERE user_email = %s", (user_email,))
    doctor = cursor.fetchone()
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
    app.run(debug=True)
