from bottle import route, run, template, request, redirect, response, abort, hook
import sqlite3
from bcrypt import gensalt, hashpw, checkpw
from os import environ


HOST='localhost'
PORT=8080

SECRET_KEY = environ.get('STORE_SECRET_KEY')
if SECRET_KEY is None:
    raise RuntimeError('環境変数 STORE_SECRET_KEY が設定されていません。')

DATABASE_FILE = 'app.db'
conn = sqlite3.connect(DATABASE_FILE)

@route('/')
def redirect_to_products():
    redirect('/products')

@route('/login')
def show_login():
    return template('''
<h1>ログイン</h1>
<!-- XSS対策 -->
<p style="color:red;"> {{ message }} </p>
<form action="/login" method="post">
<p>メールアドレス <input name="email" type="text" placeholder="user1@example.com" value="user1@example.com" /></p>
<p>パスワード <input name="password" type="password" placeholder="password1" value="password1" /></p>
<p><input value="ログイン" type="submit" /></p>
</form>''', message=request.query.message)

def hash_password(password):
    salt = gensalt()
    return hashpw(password.encode('utf-8'), salt).decode()

def is_valid_password(user_password, hashed_password):
    return checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

def query_user(email, password):
    cur = conn.cursor()
    hashed_password, user_id, nickname = cur.execute('SELECT hashed_password, id, nickname FROM users WHERE email = ?;', (email,)).fetchone()
    if hashed_password is not None and is_valid_password(password, hashed_password):
        return user_id, nickname
    return None

@route('/login', method="post")
def do_login():
    email = request.forms.email
    password = request.forms.password
    user_id, nickname = query_user(email, password)
    if user_id is None:
        print('Login faild: user_id is ' + user_id)
        return redirect('/login?message=ログインに失敗しました。')
    # CSRF対策
    response.set_cookie('user_id', user_id, secret=SECRET_KEY, path='/', httponly=True, samesite='lax')
    response.set_cookie('nickname', nickname, secret=SECRET_KEY, path='/', httponly=True, samesite='lax')
    redirect('/products')

@route('/logout')
def do_logout():
    response.delete_cookie('user_id', secret=SECRET_KEY, path='/')
    response.delete_cookie('nickname', secret=SECRET_KEY, path='/')
    redirect('/login?message=ログアウトしました。')

@route('/products')
def list_products():
    nickname = request.get_cookie("nickname", secret=SECRET_KEY)
    if nickname is None:
        redirect('/login?message=ログインしてください。')
    cur = conn.cursor()
    query = request.query.q
    if query is not None:
        # SQLインジェクション対策
        results = cur.execute("SELECT * FROM rated_products WHERE name LIKE ?;", ("%" + query + "%",)).fetchall()
    else:
        results = cur.execute('SELECT * FROM rated_products;').fetchall()
    print(results)
    return template('''
<p>ようこそ、{{ nickname }}さん（<a href="/logout">ログアウト</a>）</p>
<h1>商品一覧</h1>
<form action="/products" method="get">
  <p>商品名で検索 <input type="text" name="q" value="{{ query }}" /><input type="submit" value="検索" />
</form>
<table border="1">
  <tr>
    <th>商品名</th><th>説明</th><th>画像</th><th>価格</th><th>評価</th><th>操作</th>
  </tr>
  %for p in products:
  <tr>
    <td>{{ p[1] }}</td><td>{{ p[2] }}</td><td><img src="{{ p[3] }}"</td><td>{{ p[4] }}円</td><td>{{ p[5] }}</td><td><p><a href="/products/{{ p[0] }}">詳細</a></p><p><a href="#" onclick="alert('{{ p[1] }}を購入しました')">購入</a></p></td>
  </tr>
  %end
</table>''', nickname=nickname, products=results, query=query)

@route('/products/<product_id>')
def show_product(product_id):
    nickname = request.get_cookie("nickname", secret=SECRET_KEY)
    if nickname is None:
        redirect('/login?message=ログインしてください。')
    user_id = request.get_cookie('user_id', secret=SECRET_KEY)
    cur = conn.cursor()
    product = cur.execute('SELECT * FROM products WHERE id = ?;', (product_id,)).fetchone()
    if product is None:
        abort(400, '該当する商品がありません。')
    reviews = cur.execute('SELECT r.rate, r.comment, u.id, u.nickname FROM reviews r JOIN users u ON r.product_id = ? AND r.user_id = u.id;', (product_id,)).fetchall()
    rate = 0
    comments = []
    my_comment = None
    my_rate = None
    for review in reviews:
        rate += review[0]
        comments.append('【★' + str(review[0]) + '】' + review[1] + ' (' + review[3] + ')')
        if review[2] == user_id:
            my_rate = review[0]
            my_comment = review[1]
    if rate > 0:
        rate = round(rate / len(reviews), 1)
    else:
        rate = '無し'
    return template('''
<p>ようこそ、{{ nickname }}さん（<a href="/logout">ログアウト</a>）</p>
<h1><a href="/products">商品一覧</a> > {{ product[1] }}</h1>
<table border="1">
  <tr><th>項目</th><th>内容</th></tr>
  <tr><td>商品名</td><td>{{ product[1] }}</td></tr>
  <tr><td>説明</td><td>{{ product[2] }}</td></tr>
  <tr><td>画像</td><td><img src="{{ product[3] }}"></td></tr>
  <tr><td>価格</td><td>{{ product[4] }}円</td></tr>
  <tr><td>評価</td><td>{{ rate }}</td></tr>
  <tr>
    <td>コメント</td>
    <td>
      <ul style="list-style: none; padding-left: 0; margin-bottom: 0;">
      %for comment in comments:
        <!-- XSS対策 -->
        <li>{{ comment }}</li>
      %end
      </ul>
    </td>
  </tr>
</table>
<p><button onclick="alert('{{ product[1] }} を購入しました。')">購入</button></p>
<form action="/reviews" method="post">
  <p>あなたの評価
    <select name="rate">
    %for i in range(5, 0, -1):
      <option value="{{ str(i) }}" {{ 'selected' if i == my_rate else '' }}>{{ str(i) }}</option>
    %end
    </select>
  </p>
%if my_comment is None:
  <p>あなたのコメント<input type="text" name="comment" /></p>
%else:
  <p>あなたのコメント<input type="text" name="comment" value="{{ my_comment }}" /></p>
%end
  <p><input type="submit" value="投稿" /></p>
  <input type="hidden" name="product_id" value="{{ product[0] }}" />
</form>
%if my_comment is not None:
<form action="/reviews" method="post">
  <input type="hidden" name="_method" value="delete" />
  <input type="hidden" name="product_id" value="{{ product[0] }}" />
  <input type="submit" value="削除" />
</form>
%end
''', nickname=nickname, product=product, rate=rate, comments=comments, my_rate=my_rate, my_comment=my_comment)

@route('/reviews', method='post')
def add_review():
    user_id = request.get_cookie("user_id", secret=SECRET_KEY)
    if user_id is None:
        redirect('/login?message=ログインしてください。')
    product_id = request.forms.product_id
    if product_id is None:
        abort(400, '該当する商品がありません。')
    if request.forms._method == 'delete':
        cur = conn.cursor()
        cur.execute('DELETE FROM reviews WHERE product_id = ? AND user_id = ?;', (product_id, user_id))
        conn.commit()
        redirect('/products/' + product_id)
    rate = request.forms.rate
    if int(rate) < 1 or int(rate) > 5:
        abort(400, '評価の値が不正です。')
    comment = request.forms.comment
    if comment is None:
        comment = ''
    cur = conn.cursor()
    review = cur.execute('SELECT * FROM reviews r WHERE r.product_id = ? AND r.user_id = ?', (product_id, user_id)).fetchone()
    if review is None:
        cur.execute('INSERT INTO reviews(product_id, user_id, rate, comment) VALUES (?, ?, ?, ?)', (product_id, user_id, rate, comment))
        conn.commit()
    else:
        cur.execute('UPDATE reviews SET rate = ?, comment = ? WHERE product_id = ? AND user_id = ?', (rate, comment, product_id, user_id))
        conn.commit()
    redirect('/products')

@hook('after_request')
def protect():
    # クリックジャッキング対策
    response.headers['X-Frame-Options'] = 'DENY'

run(host=HOST, port=PORT, reloader=True)