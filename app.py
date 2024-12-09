from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime


# Initialise the Flask application
app = Flask(__name__)
app.secret_key = '123'

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Check uploaded file is an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        ORDER BY created_at DESC
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_entry', methods=['POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'image' not in request.files:
        flash('No image uploaded', 'error')
        return redirect(url_for('index'))

    file = request.files['image']
    if file.filename == '':
        flash('No image selected', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        db = get_db()
        db.execute('''
            INSERT INTO entries (user_id, title, description, image_path)
            VALUES (?, ?, ?, ?)
        ''', (
            session['user_id'],
            request.form['title'],
            request.form['description'],
            f"uploads/{filename}"
        ))
        db.commit()

        flash('Entry added successfully!', 'success')
    else:
        flash('Invalid file type', 'error')

    return redirect(url_for('index'))

# Define the route for offline functionality
@app.route('/offline')
def offline():
    response = make_response(render_template('offline.html'))
    return response

# Define the route for the service worker
@app.route('/service-worker.js')
def sw():
    response = make_response(
        send_from_directory(os.path.join(app.root_path, 'static/js'),
        'service-worker.js')
    )
    return response

# Define the route for the manifest.json file
@app.route('/manifest.json')
def manifest():
    response = make_response(
        send_from_directory(os.path.join(app.root_path, 'static'),
        'manifest.json')
    )
    return response

@app.route('/edit_entry/<int:entry_id>', methods=['POST'])
def edit_entry(entry_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    # First verify the entry belongs to the current user
    entry = db.execute(
        'SELECT * FROM entries WHERE id = ? AND user_id = ?',
        (entry_id, session['user_id'])
    ).fetchone()

    if not entry:
        flash('Entry not found or access denied', 'error')
        return redirect(url_for('index'))

    # Update the title and description
    title = request.form['title']
    description = request.form['description']

    # Check if a new image was uploaded
    if 'image' in request.files and request.files['image'].filename != '':
        file = request.files['image']
        if allowed_file(file.filename):
            # Delete the old image file
            try:
                old_image_path = os.path.join(app.root_path, 'static', entry['image_path'])
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            except Exception as e:
                print(f"Error deleting old image: {e}")

            # Save the new image
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Update database with new image path
            db.execute('''
                UPDATE entries
                SET title = ?, description = ?, image_path = ?
                WHERE id = ? AND user_id = ?
            ''', (title, description, f"uploads/{filename}", entry_id, session['user_id']))
        else:
            flash('Invalid file type', 'error')
            return redirect(url_for('index'))
    else:
        # Update database without changing the image
        db.execute('''
            UPDATE entries
            SET title = ?, description = ?
            WHERE id = ? AND user_id = ?
        ''', (title, description, entry_id, session['user_id']))

    db.commit()
    flash('Entry updated successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    # First get the entry to find the image path
    entry = db.execute(
        'SELECT * FROM entries WHERE id = ? AND user_id = ?',
        (entry_id, session['user_id'])
    ).fetchone()

    if not entry:
        flash('Entry not found or access denied', 'error')
        return redirect(url_for('index'))

    # Delete the image file
    try:
        image_path = os.path.join(app.root_path, 'static', entry['image_path'])
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception as e:
        print(f"Error deleting image file: {e}")

    # Delete the database entry
    db.execute('DELETE FROM entries WHERE id = ? AND user_id = ?',
               (entry_id, session['user_id']))

    db.commit()
    flash('Entry deleted successfully!', 'success')
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True, port=5000)
