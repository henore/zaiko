from flask import Flask, render_template, request, jsonify
import sqlite3
from functools import wraps
from flask import session, redirect, url_for
import os
import hashlib
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
       if hashlib.sha256(request.form['password'].encode()).hexdigest() == '8fd3b9cc91f87b6996012fbe0e5d1643f9d0da46f72ae36fbc986aef47d4fe83':
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
    month = request.args.get('month')
    conn = get_db()
    cursor = conn.cursor()
    try:
        if month:
            cursor.execute('''
                SELECT s.rowid as id, s.date, p.name, p.color, p.size, s.quantity, s.price, s.shipping_fee, s.bundle_id,
                       CAST(s.price - CAST(s.price * 0.1 AS INTEGER) - COALESCE(s.shipping_fee, 0) AS INTEGER) as profit,
                       strftime('%Y-%m', s.date) as month
                FROM sales s
                JOIN products p ON s.product_id = p.id
                WHERE strftime('%Y-%m', s.date) = ?
                ORDER BY s.date DESC
            ''', (month,))
        else:
            cursor.execute('''
                SELECT s.rowid as id, s.date, p.name, p.color, p.size, s.quantity, s.price, s.shipping_fee, s.bundle_id,
                       CAST(s.price - CAST(s.price * 0.1 AS INTEGER) - COALESCE(s.shipping_fee, 0) AS INTEGER) as profit,
                       strftime('%Y-%m', s.date) as month
                FROM sales s
                JOIN products p ON s.product_id = p.id
                WHERE s.date >= date('now', '-12 months')
                ORDER BY s.date DESC
            ''')

        sales = [dict(row) for row in cursor.fetchall()]
        return jsonify(sales)
    except Exception as e:
        print('get_sales_data error:', str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/update_sale', methods=['POST'])
def update_sale():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id FROM products
            WHERE name = ? AND color = ? AND (size = ? OR (size IS NULL AND ? IS NULL))
        ''', (data['name'], data['color'], data['size'], data['size']))
        product = cursor.fetchone()
        if not product:
            return jsonify({'success': False, 'error': '商品が見つかりません'})

        shipping_fee = data.get('shipping_fee')
        cursor.execute('''
            UPDATE sales
            SET date = ?, product_id = ?, quantity = ?, price = ?, shipping_fee = ?, bundle_id = ?
            WHERE rowid = ?
        ''', (data['date'], product[0], data['quantity'], data['price'], shipping_fee, data['bundle_id'], data['id']))

        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': '売上データが見つかりません'})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)