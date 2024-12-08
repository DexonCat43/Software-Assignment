from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Initialise the Flask application
app = Flask(__name__)
app.secret_key = '123'

def get_db():
    db = sqlite3.connect('database/photo_journal.db')
    db.row_factory = sqlite3.Row
    return db

# Define the route for the homepage
@app.route('/')
def index():
    # Check if the user is logged in by verifying the session
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to the login page if not authenticated

    db = get_db()
    entries = db.execute('''
        SELECT * FROM entries
        WHERE user_id =?
        ORDER BY date DESC
''', (session['user_id'],)).fetchall()

    return render_template('index.html', entries=entries)
# Define the route for login functionality, supporting GET and POST methods

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

    
    if user and check_password_hash(user['password'], password):
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('index'))
    
    flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        try:
            #try to insert the new user.
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()
            flash('Registration successful! Please log in.', 'success') #message to display if successful.
            return redirect(url_for('login'))
        except sqlite3.IntegrityError: # catch the exception here.
            flash('Username already exists!', 'error') #message to display if it failed.

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
