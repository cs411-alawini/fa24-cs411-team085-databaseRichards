from flask import Flask, render_template, request, redirect, flash
import mysql.connector
import random

app = Flask(__name__)
app.secret_key = "your_secret_key"

db_config = {
    'user': 'root',
    'password': '',
    'host': '34.136.188.227',
    'database': 'SportsBettingDB'
}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            query = "SELECT * FROM UserInfo WHERE Username = %s AND Password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            if user:
                flash(f"Welcome back, {user['Username']}!", "success")
                return redirect('/')
            else:
                flash("Invalid username or password.", "danger")

        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")

        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        userId = random.randint(3000, 9999)

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            query = "INSERT INTO UserInfo (UserID, Username, Email, Password) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (userId, username, email, password))
            conn.commit()

            flash("User registered successfully!", "success")
            return redirect('/login')

        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")

        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
