from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# Initialize the Flask application
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

#Database configure
def get_db():
    db = sqlite3.connect('database/movie_reviews.db')
    db.row_factory = sqlite3.Row
    return db

#index page route
@app.route('/')
def index():
    db = get_db()
    reviews = db.execute('''
        SELECT reviews.*, users.username FROM reviews
        JOIN users ON reviews.user_id = users.id
        ORDER BY reviews.created_at DESC
    ''').fetchall()

    return render_template('index.html', reviews=reviews)

#login routefunctionality
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')

# Define the route for the register functionality
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Handle POST request when the user submits the registration form
    if request.method == 'POST':
        username = request.form['username']  # Get the username from the form
        password = request.form['password']  # Get the password from the form

        db = get_db()
        try:
            # Insert the new user into the users table with a hashed password
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()  # Commit the changes to the database
            flash('Registration successful! Please log in.', 'success')  # Show a success message
            return redirect(url_for('login'))  # Redirect to the login page
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')  # Show an error message if the username already exists

    # Render the registration template for GET requests
    return render_template('register.html')

#route for the logoout functionality
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Define the route for adding a review
@app.route('/add_review', methods=['POST'])
def add_review():
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    # Check if a poster file was uploaded
    if 'poster' not in request.files:
        flash('No poster uploaded', 'error')
        return redirect(url_for('index'))  # Redirect to homepage if no poster is uploaded

    file = request.files['poster']
    # Check if the uploaded file has a valid filename
    if file.filename == '':
        flash('No poster selected', 'error')
        return redirect(url_for('index'))

    # Check if the file type is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)  # Save the file to the configured upload folder

        db = get_db()
        # Insert the new review into the database
        db.execute('''
            INSERT INTO reviews (user_id, movie_title, review, rating, poster_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            session['user_id'],  
            request.form['movie_title'],  
            request.form['review'],  
            request.form['rating'],  
            f"uploads/{filename}"  
        ))
        db.commit()  # Commit the changes to the database

        flash('Review added successfully!', 'success')  # Show a success message
    else:
        flash('Invalid file type', 'error')  # Show an error message if the file type is not allowed

    return redirect(url_for('index'))  # Redirect to the homepage

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


# Define the route for the review edit functionality
@app.route('/edit_review/<int:review_id>', methods=['POST'])
def edit_review(review_id):
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    db = get_db()
    # Retrieve the review to verify it belongs to the logged-in user
    review = db.execute(
        'SELECT * FROM reviews WHERE id = ? AND user_id = ?',
        (review_id, session['user_id'])
    ).fetchone()

    # If review not found or access is denied show an error message
    if not review:
        flash('Review not found or access denied', 'error')
        return redirect(url_for('index'))

    # Get the updated movie title review text and rating from the form
    movie_title = request.form['movie_title']
    review_text = request.form['review']
    rating = request.form['rating']
    poster_path = review['poster_path']  # Keep the current poster path

    # Check if a new poster file is uploaded
    if 'poster' in request.files and request.files['poster'].filename != '':
        file = request.files['poster']
        if allowed_file(file.filename):
            try:
                # Delete the old poster file
                old_poster_path = os.path.join(app.root_path, 'static', review['poster_path'])
                if os.path.exists(old_poster_path):
                    os.remove(old_poster_path)
            except Exception as e:
                print(f"Error deleting old poster: {e}")

            # Save the new poster file
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            poster_path = f"uploads/{filename}"  # Update the poster path

    # Update the review in the database
    db.execute('''
        UPDATE reviews
        SET movie_title = ?, review = ?, rating = ?, poster_path = ?
        WHERE id = ? AND user_id = ?
    ''', (movie_title, review_text, rating, poster_path, review_id, session['user_id']))
    db.commit()

    # Flash a success message and redirect to the homepage
    flash('Review updated successfully!', 'success')
    return redirect(url_for('index'))

# Define the route for the review delete functionality
@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    db = get_db()
    # Retrieve the review to verify it belongs to the logged-in user
    review = db.execute(
        'SELECT * FROM reviews WHERE id = ? AND user_id = ?',
        (review_id, session['user_id'])
    ).fetchone()

    # If review not found or access is denied, show an error message
    if not review:
        flash('Review not found or access denied', 'error')
        return redirect(url_for('index'))

    # Try to delete the poster file associated with the review
    try:
        poster_path = os.path.join(app.root_path, 'static', review['poster_path'])
        if os.path.exists(poster_path):
            os.remove(poster_path)
    except Exception as e:
        print(f"Error deleting poster file: {e}")

    # Delete the review from the database
    db.execute('DELETE FROM reviews WHERE id = ? AND user_id = ?', (review_id, session['user_id']))
    db.commit()
    
    # Flash a success message and redirect to the homepage
    flash('Review deleted successfully!', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
