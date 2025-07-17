from flask import Flask, render_template, request, jsonify
import sqlite3
from functools import wraps
from flask import session, redirect, url_for
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
def login_required(f):
   @wraps(f)
   def decorated_function(*args, **kwargs):
       if 'logged_in' not in session:
           return redirect(url_for('login'))
       return f(*args, **kwargs)
   return decorated_function

@app.route('/login', methods=['GET', 'POST'])

def login():
   if request.method == 'POST':
       if request.form['password'] == '':  # パスワードを設定　コミット用に平文パスワードを一時的に削除
           session['logged_in'] = True
           return redirect(url_for('index'))
       return 'パスワードが違います'
   return render_template('login.html')
def get_db():
    conn = sqlite3.connect('/home/happybeautiful/mysite/inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
@login_required
def index():
   return render_template('index.html')

@app.route('/products', methods=['GET'])
def get_products():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, color, size, quantity FROM products ORDER BY name, color, quantity DESC')
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)

@app.route('/edit_product', methods=['POST'])
def edit_product():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE products
            SET name = ?, color = ?, size = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ? AND color = ? AND (size = ? OR (size IS NULL AND ? IS NULL))
        ''', (
            data['new_name'], data['new_color'], data['new_size'],
            data['old_name'], data['old_color'], data['old_size'], data['old_size']
        ))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'データが見つかりません'})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO products (name, color, size, quantity)
            VALUES (?, ?, ?, ?)
        ''', (data['name'], data['color'], data.get('size'), data['quantity']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/update_stock', methods=['POST'])
def update_stock():
    data = request.json
    print("Received data:", data)  # デバッグログ
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE products
            SET quantity = quantity + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ? AND color = ? AND (size = ? OR (size IS NULL AND ? IS NULL))
        ''', (data['quantity'], data['name'], data['color'], data['size'], data['size']))
        print("Rows affected:", cursor.rowcount)  # デバッグログ
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print("Error:", str(e))  # デバッグログ
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/register_sale', methods=['POST'])
def register_sale():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 商品IDの取得
        cursor.execute('''
            SELECT id FROM products
            WHERE name = ? AND color = ? AND (size = ? OR (size IS NULL AND ? IS NULL))
        ''', (data['name'], data['color'], data['size'], data['size']))
        product_id = cursor.fetchone()[0]

        # 在庫減少
        cursor.execute('''
            UPDATE products
            SET quantity = quantity - ?
            WHERE id = ?
        ''', (data['quantity'], product_id))

        # 売上登録
        cursor.execute('''
            INSERT INTO sales (date, product_id, quantity, price, shipping_fee, bundle_id)
            VALUES (date('now'), ?, ?, ?, ?, ?)
        ''', (product_id, data['quantity'], data['price'], data['shipping_fee'], data['bundle_id']))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(str(e))  # エラーログ追加
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/sales', methods=['GET'])
def show_sales():
   return render_template('sales.html')

@app.route('/get_sales_data', methods=['GET'])
def get_sales_data():
    # month パラメータがある場合は特定の月のデータを取得、なければ過去12ヶ月
    month = request.args.get('month')
    conn = get_db()
    cursor = conn.cursor()

    if month:
        # 特定の月のデータを取得
        cursor.execute('''
            SELECT s.date, p.name, p.color, p.size, s.quantity, s.price, s.shipping_fee, s.bundle_id,
                   CAST(s.price - CAST(s.price * 0.1 AS INTEGER) - s.shipping_fee AS INTEGER) as profit,
                   strftime('%Y-%m', s.date) as month
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE strftime('%Y-%m', s.date) = ?
            ORDER BY s.date DESC
        ''', (month,))
    else:
        # 過去12ヶ月のデータを取得
        cursor.execute('''
            SELECT s.date, p.name, p.color, p.size, s.quantity, s.price, s.shipping_fee, s.bundle_id,
                   CAST(s.price - CAST(s.price * 0.1 AS INTEGER) - s.shipping_fee AS INTEGER) as profit,
                   strftime('%Y-%m', s.date) as month
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE s.date >= date('now', '-12 months')
            ORDER BY s.date DESC
        ''')

    sales = [dict(row) for row in cursor.fetchall()]
    return jsonify(sales)

if __name__ == '__main__':
    app.run(debug=True)