import sqlite3
conn = sqlite3.connect('techcommerce.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS product_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER,
    reviewer_name VARCHAR(100) NOT NULL,
    reviewer_email VARCHAR(255),
    rating INTEGER NOT NULL,
    title VARCHAR(200),
    comment TEXT NOT NULL,
    is_verified BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
)''')
conn.commit()
print('Table created')
conn.close()
