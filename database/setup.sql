--CREATE TABLE IF NOT EXISTS users(
--    id INTEGER PRIMARY KEY AUTOINCREMENT,
--    username TEXT UNIQUE NOT NULL,
--    password TEXT NOT NULL
--);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    image_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) references users (id)
);