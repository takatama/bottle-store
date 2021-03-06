import sqlite3
from random import randrange
import uuid
import hashlib
from bcrypt import gensalt, hashpw


DATABASE_FILE = 'app.db'
EVIL_DATABASE_FILE = 'evil.db'

def hash_password(password):
    salt = gensalt()
    return hashpw(password.encode('utf-8'), salt).decode()

# append mode。もしファイルが存在していなければ作成する。
open(DATABASE_FILE, 'a').close()
open(EVIL_DATABASE_FILE, 'a').close()

conn = sqlite3.connect(DATABASE_FILE)
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS products;')
cur.execute('CREATE TABLE products(id INTEGER PRIMARY KEY AUTOINCREMENT, name STRING, description STRING, image_url STRING, price_yen INTEGER);')
# 9つの商品を登録する。
products = []
for i in range(1, 10):
    products.append(('商品' + str(i), '商品' + str(i) + 'の説明', 'https://via.placeholder.com/150', randrange(1, 100) * 100))
cur.executemany('INSERT INTO products(name, description, image_url, price_yen) values (?, ?, ?, ?);', products)

cur.execute('DROP TABLE IF EXISTS users;')
cur.execute('CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, email STRING, hashed_password STRING, nickname STRING);')
# 9人のユーザーを登録する。
users = []
for i in range(1, 10):
    users.append(('user' + str(i) + '@example.com', hash_password('password' + str(i)), 'ユーザー' + str(i)))
cur.executemany('INSERT INTO users(email, hashed_password, nickname) values(?, ?, ?)', users)

cur.execute('DROP TABLE IF EXISTS reviews;')
cur.execute('CREATE TABLE reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_id INTEGER, rate INTEGER, comment STRING, foreign key(product_id) references products(id), foreign key(user_id) references users(id))')
reviews = []
for i in range(1, 10):
    product_id = randrange(1, 10)
    user_id = randrange(1, 10)
    rate = randrange(1, 6)
    reviews.append((product_id, user_id, rate, '...'))
cur.executemany('INSERT INTO reviews(product_id, user_id, rate, comment) values(?, ?, ?, ?)', reviews)

cur.execute('DROP VIEW IF EXISTS rated_products;')
cur.execute('CREATE VIEW rated_products as SELECT p.id, p.name, p.description, p.image_url, p.price_yen, IFNULL(ROUND(AVG(r.rate), 1), "無し") FROM products AS p LEFT OUTER JOIN reviews AS r ON p.id = r.product_id GROUP BY p.id')
conn.commit()

for row in cur.execute('SELECT * FROM products;').fetchall():
    print(row)

for row in cur.execute('SELECT * FROM users;').fetchall():
    print(row)

for row in cur.execute('SELECT * FROM reviews;').fetchall():
    print(row)

for row in cur.execute('SELECT * FROM rated_products;').fetchall():
    print(row)

conn.close()

evil_conn = sqlite3.connect(EVIL_DATABASE_FILE)
evil_cur = evil_conn.cursor()
evil_cur.execute('DROP TABLE IF EXISTS users;')
evil_cur.execute('CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, datetime STRING, email STRING, password STRING);')
evil_conn.commit()
