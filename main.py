from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
import hashlib
import datetime
import qrcode
import io
import base64
from functools import wraps

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("SECRET_KEY", "baba-jadugar-super-secret-key-2026")
CORS(app)

DB_PATH = "database.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Settings
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        upi_id TEXT DEFAULT 'yourupi@paytm',
        mini_app_name TEXT DEFAULT 'Premium Group Hub',
        bill_description TEXT DEFAULT 'Digital Course Access - Lifetime',
        admin_password TEXT DEFAULT 'baba123',
        total_views INTEGER DEFAULT 0
    )''')

    # Products - with media_type + video_url
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        video_url TEXT,
        media_type TEXT DEFAULT 'image',
        group_link TEXT,
        validity TEXT DEFAULT 'Lifetime',
        tags TEXT DEFAULT 'Premium',
        is_active INTEGER DEFAULT 1,
        views INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Safe migration for existing DBs
    try:
        c.execute("ALTER TABLE products ADD COLUMN video_url TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE products ADD COLUMN media_type TEXT DEFAULT 'image'")
    except:
        pass

    # Orders / Payments
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        product_title TEXT,
        amount REAL,
        utr TEXT,
        status TEXT DEFAULT 'pending',
        telegram_user TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        approved_at TEXT,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')

    # Insert default settings if not exists
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO settings (id, upi_id, mini_app_name, bill_description, admin_password) VALUES (1, 'yourupi@paytm', 'Premium Group Hub', 'Digital Course Access - Lifetime', 'baba123')")

    # Insert a sample product if empty
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO products (title, description, price, image_url, video_url, media_type, group_link, validity, tags)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ("Demo Digital Course", "Full HD Video Course with Lifetime Access", 499,
                   "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_Buck_Bunny_poster.jpg/800px-Big_Buck_Bunny_poster.jpg",
                   "", "image", "https://t.me/+YourPremiumGroup", "Lifetime", "Premium,VIP"))

    conn.commit()
    conn.close()

init_db()

# ---------- Helpers ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def generate_qr_base64(upi_id, amount, name="Premium Group Hub"):
    upi_string = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR&tn=Premium Access"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(upi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ---------- Public Routes ----------
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('static', 'admin.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn = get_db()
    row = conn.execute("SELECT mini_app_name, upi_id, bill_description, total_views, support_telegram FROM settings WHERE id=1").fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    conn.execute("UPDATE settings SET total_views = total_views + 1 WHERE id=1")
    products = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY id DESC").fetchall()
    conn.commit()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/product/<int:pid>', methods=['GET'])
def get_product(pid):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=? AND is_active=1", (pid,)).fetchone()
    if product:
        conn.execute("UPDATE products SET views = views + 1 WHERE id=?", (pid,))
        conn.commit()
    conn.close()
    if not product:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(product))

@app.route('/api/create-order', methods=['POST'])
def create_order():
    data = request.json
    product_id = data.get("product_id")
    utr = data.get("utr", "").strip()
    telegram_user = data.get("telegram_user", "Unknown")

    if not product_id or not utr:
        return jsonify({"error": "Product ID and UTR required"}), 400

    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    existing = conn.execute("SELECT id FROM orders WHERE utr=?", (utr,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "This UTR is already used"}), 400

    conn.execute('''INSERT INTO orders (product_id, product_title, amount, utr, status, telegram_user)
                    VALUES (?, ?, ?, ?, 'pending', ?)''',
                 (product_id, product["title"], product["price"], utr, telegram_user))
    conn.commit()
    order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    return jsonify({"success": True, "order_id": order_id, "message": "UTR submitted. Waiting for verification."})

@app.route('/api/qr/<int:pid>')
def get_qr(pid):
    conn = get_db()
    product = conn.execute("SELECT price FROM products WHERE id=?", (pid,)).fetchone()
    settings = conn.execute("SELECT upi_id, mini_app_name FROM settings WHERE id=1").fetchone()
    conn.close()
    if not product or not settings:
        return jsonify({"error": "Not found"}), 404

    qr_b64 = generate_qr_base64(settings["upi_id"], product["price"], settings["mini_app_name"])
    upi_link = f"upi://pay?pa={settings['upi_id']}&pn={settings['mini_app_name']}&am={product['price']}&cu=INR&tn=Premium Access"

    return jsonify({
        "qr_base64": qr_b64,
        "upi_link": upi_link,
        "upi_id": settings["upi_id"],
        "amount": product["price"],
        "bill_description": "Premium Access Payment"
    })

# ---------- Admin Routes ----------
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get("password", "")
    conn = get_db()
    row = conn.execute("SELECT admin_password FROM settings WHERE id=1").fetchone()
    conn.close()
    if row and password == row["admin_password"]:
        session["admin_logged_in"] = True
        return jsonify({"success": True})
    return jsonify({"error": "Wrong password"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"success": True})

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    return jsonify({"logged_in": bool(session.get("admin_logged_in"))})

@app.route('/api/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    conn = get_db()
    today = datetime.date.today().isoformat()
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

    today_earn = conn.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='approved' AND date(approved_at)=?", (today,)).fetchone()[0]
    week_earn = conn.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='approved' AND date(approved_at)>=?", (week_ago,)).fetchone()[0]
    total_earn = conn.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='approved'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_views = conn.execute("SELECT total_views FROM settings WHERE id=1").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    conn.close()
    return jsonify({
        "today_earning": today_earn,
        "week_earning": week_earn,
        "total_earning": total_earn,
        "pending_orders": pending,
        "total_orders": total_orders,
        "total_views": total_views,
        "total_products": total_products
    })

@app.route('/api/admin/products', methods=['GET', 'POST'])
@login_required
def admin_products():
    conn = get_db()
    if request.method == 'GET':
        products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(p) for p in products])

    # POST - Add product
    data = request.json
    conn.execute('''INSERT INTO products 
        (title, description, price, image_url, video_url, media_type, group_link, validity, tags, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get("title"), data.get("description"), float(data.get("price", 0)),
         data.get("image_url"), data.get("video_url"), data.get("media_type", "image"),
         data.get("group_link"), data.get("validity", "Lifetime"),
         data.get("tags", "Premium"), 1 if data.get("is_active", True) else 0))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/admin/products/<int:pid>', methods=['PUT', 'DELETE'])
@login_required
def admin_product_detail(pid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # PUT - Update
    data = request.json
    conn.execute('''UPDATE products SET 
        title=?, description=?, price=?, image_url=?, video_url=?, media_type=?,
        group_link=?, validity=?, tags=?, is_active=? WHERE id=?''',
        (data.get("title"), data.get("description"), float(data.get("price", 0)),
         data.get("image_url"), data.get("video_url"), data.get("media_type", "image"),
         data.get("group_link"), data.get("validity", "Lifetime"),
         data.get("tags", "Premium"), 1 if data.get("is_active", True) else 0, pid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/admin/orders', methods=['GET'])
@login_required
def admin_orders():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])

@app.route('/api/admin/orders/<int:oid>/approve', methods=['POST'])
@login_required
def approve_order(oid):
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    conn.execute("UPDATE orders SET status='approved', approved_at=? WHERE id=?", (now, oid))
    conn.commit()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    product = conn.execute("SELECT group_link FROM products WHERE id=?", (order["product_id"],)).fetchone() if order else None
    conn.close()
    return jsonify({
        "success": True,
        "group_link": product["group_link"] if product else None
    })

@app.route('/api/admin/orders/<int:oid>/reject', methods=['POST'])
@login_required
def reject_order(oid):
    conn = get_db()
    conn.execute("UPDATE orders SET status='rejected' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    conn = get_db()
    if request.method == 'GET':
        row = conn.execute("SELECT upi_id, mini_app_name, bill_description, admin_password FROM settings WHERE id=1").fetchone()
        conn.close()
        return jsonify(dict(row))

    data = request.json
    conn.execute('''UPDATE settings SET upi_id=?, mini_app_name=?, bill_description=?, admin_password=? WHERE id=1''',
                 (data.get("upi_id"), data.get("mini_app_name"), data.get("bill_description"), data.get("admin_password")))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/check-order-status', methods=['POST'])
def check_order_status():
    data = request.json
    utr = data.get("utr", "").strip()
    if not utr:
        return jsonify({"error": "UTR required"}), 400
    conn = get_db()
    order = conn.execute("SELECT o.*, p.group_link FROM orders o LEFT JOIN products p ON o.product_id = p.id WHERE o.utr=?", (utr,)).fetchone()
    conn.close()
    if not order:
        return jsonify({"status": "not_found"})
    return jsonify({
        "status": order["status"],
        "group_link": order["group_link"] if order["status"] == "approved" else None,
        "product_title": order["product_title"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
