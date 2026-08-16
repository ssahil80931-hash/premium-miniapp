import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

def init_db():
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    
    # Products table (Day access & video/group link included)
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        title TEXT, 
        description TEXT, 
        price TEXT, 
        btn_text TEXT, 
        video_url TEXT, 
        group_link TEXT,
        day_access TEXT)""")
        
    # Config table (Romantic/Club theme, Admin Credentials, QR Note)
    c.execute("""CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        upi_id TEXT,
        qr_image TEXT,
        theme_color TEXT,
        enable_animation BOOLEAN,
        admin_user TEXT,
        admin_pass TEXT,
        payment_note TEXT)""")
        
    # Orders table
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        user_name TEXT,
        product_id INTEGER,
        utr TEXT,
        status TEXT DEFAULT 'pending')""")

    # Analytics table (For real visit counts)
    c.execute("""CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visits INTEGER DEFAULT 0)""")

    # Default Analytics Row
    c.execute("SELECT COUNT(*) FROM analytics")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO analytics (visits) VALUES (0)")

    # Default Config
    c.execute("SELECT COUNT(*) FROM config")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO config (upi_id, qr_image, theme_color, enable_animation, admin_user, admin_pass, payment_note)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  ("clubmaza@upi", "", "#ff007f", True, "admin", "admin123", "💖 Scan QR & Pay via any UPI App, enter UTR below to unlock VIP Club access!"))

    # Default Product
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO products (title, description, price, btn_text, video_url, group_link, day_access)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  ("VIP Romantic Club Pass", "Exclusive access to private media & community.", "99", "UNLOCK NOW 💋", "", "https://t.me/+example_vip_link", "30 Days"))

    conn.commit()
    conn.close()

init_db()

class AdminLogin(BaseModel):
    username: str
    password: str

class ProductModel(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = ""
    price: str
    btn_text: Optional[str] = "UNLOCK NOW 💋"
    video_url: Optional[str] = ""
    group_link: Optional[str] = ""
    day_access: Optional[str] = "Lifetime"

class DeleteProductModel(BaseModel):
    id: int

class OrderActionModel(BaseModel):
    order_id: int

class SettingsModel(BaseModel):
    upi_id: str
    qr_image: Optional[str] = ""
    theme_color: Optional[str] = "#ff007f"
    enable_animation: Optional[bool] = True
    admin_user: str
    admin_pass: str
    payment_note: Optional[str] = ""

class OrderSubmitModel(BaseModel):
    user_id: str
    user_name: str
    product_id: int
    utr_proof: str


@app.post("/api/admin/login")
def admin_login(data: AdminLogin):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    c.execute("SELECT admin_user, admin_pass FROM config LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row and data.username == row[0] and data.password == row[1]:
        return {"status": "success", "token": "mazakarlo_secure_token"}
    return {"status": "error", "message": "Invalid credentials"}


@app.get("/api/admin/dashboard")
def admin_dashboard():
    conn = sqlite3.connect("store_database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM config LIMIT 1")
    config = c.fetchone()
    
    c.execute("SELECT * FROM products")
    products = [dict(row) for row in c.fetchall()]
    
    c.execute("""
        SELECT o.id, o.user_id, o.user_name, o.utr, o.status, p.title, p.price, p.group_link 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        ORDER BY o.id DESC
    """)
    orders = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT SUM(CAST(p.price AS INTEGER)) FROM orders o JOIN products p ON o.product_id = p.id WHERE o.status = 'approved'")
    rev = c.fetchone()[0]
    revenue = rev if rev else 0
    
    c.execute("SELECT visits FROM analytics LIMIT 1")
    visits_row = c.fetchone()
    total_visits = visits_row[0] if visits_row else 0

    c.execute("SELECT COUNT(DISTINCT user_id) FROM orders WHERE status='approved'")
    total_buyers = c.fetchone()[0]
    
    conn.close()
    
    return {
        "revenue": revenue,
        "total_visits": total_visits,
        "total_buyers": total_buyers,
        "orders": orders,
        "products": products,
        "admin_user": config["admin_user"] if config else "admin",
        "admin_pass": config["admin_pass"] if config else "admin123",
        "payment_note": config["payment_note"] if config else ""
    }


@app.post("/api/admin/save-product")
def save_product(p: ProductModel):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    if p.id:
        c.execute("""UPDATE products SET title=?, description=?, price=?, btn_text=?, video_url=?, group_link=?, day_access=? WHERE id=?""",
                  (p.title, p.description, p.price, p.btn_text, p.video_url, p.group_link, p.day_access, p.id))
    else:
        c.execute("""INSERT INTO products (title, description, price, btn_text, video_url, group_link, day_access) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (p.title, p.description, p.price, p.btn_text, p.video_url, p.group_link, p.day_access))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/admin/delete-product")
def delete_product(data: DeleteProductModel):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (data.id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/admin/approve-order")
def approve_order(data: OrderActionModel):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='approved' WHERE id=?", (data.order_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/admin/reject-order")
def reject_order(data: OrderActionModel):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='rejected' WHERE id=?", (data.order_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/admin/update-settings")
def update_settings(s: SettingsModel):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    c.execute("""UPDATE config SET upi_id=?, qr_image=?, theme_color=?, enable_animation=?, admin_user=?, admin_pass=?, payment_note=? WHERE id=1""",
              (s.upi_id, s.qr_image, s.theme_color, s.enable_animation, s.admin_user, s.admin_pass, s.payment_note))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/api/data")
def get_store_data():
    conn = sqlite3.connect("store_database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Increment total visit count on mini app open
    c.execute("UPDATE analytics SET visits = visits + 1")
    conn.commit()
    
    c.execute("SELECT * FROM products")
    products = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT upi_id, qr_image, theme_color, payment_note FROM config LIMIT 1")
    cfg = c.fetchone()
    conn.close()
    
    return {
        "products": products,
        "config": {
            "upi_id": cfg["upi_id"] if cfg else "",
            "qr_image": cfg["qr_image"] if cfg else "",
            "theme_color": cfg["theme_color"] if cfg else "#ff007f",
            "payment_note": cfg["payment_note"] if cfg else ""
        }
    }


@app.post("/api/order/submit")
def submit_order(order: OrderSubmitModel):
    conn = sqlite3.connect("store_database.db")
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, user_name, product_id, utr, status) VALUES (?, ?, ?, ?, 'pending')",
              (order.user_id, order.user_name, order.product_id, order.utr_proof))
    conn.commit()
    conn.close()
    return {"status": "success", "order_status": "pending"}


@app.get("/api/order/check-status")
def check_order_status(user_id: str):
    conn = sqlite3.connect("store_database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT o.status, p.group_link, p.title 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE o.user_id = ? ORDER BY o.id DESC LIMIT 1
    """, (user_id,))
    row = c.fetchone()
    conn.save = conn.close()
    if row:
        return {"status": row["status"], "group_link": row["group_link"] if row["status"] == "approved" else ""}
    return {"status": "not_found"}

from fastapi.responses import FileResponse
import os

@app.get("/")
async def serve_index():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"detail": "Not Found"}

@app.get("/admin")
async def serve_admin():
    if os.path.exists("static/admin.html"):
        return FileResponse("static/admin.html")
    return {"detail": "Not Found"}
    
