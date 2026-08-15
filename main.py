import os
import sqlite3
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "store_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT, description TEXT, price TEXT,
                    btn_text TEXT, video_url TEXT, group_link TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT, user_name TEXT, product_id INTEGER,
                    product_title TEXT, price TEXT, utr_proof TEXT,
                    status TEXT, group_link TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY, upi_id TEXT, qr_image TEXT,
                    theme_color TEXT, enable_animation INTEGER,
                    admin_user TEXT, admin_pass TEXT, payment_note TEXT)''')
    
    try:
        c.execute("ALTER TABLE config ADD COLUMN payment_note TEXT DEFAULT 'Scan QR code and complete payment. Enter UTR below for instant verification.'")
    except:
        pass

    c.execute("SELECT COUNT(*) FROM config")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO config VALUES 
                     (1, 'merchant@upi', 'https://via.placeholder.com/250', '#00ff9d', 1, 'admin', 'admin123', 
                     'Scan QR code and complete payment. Enter UTR below for instant verification.')""")
    
    conn.commit()
    conn.close()

init_db()

class LoginSchema(BaseModel):
    username: str
    password: str

class ProductSchema(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    price: str
    btn_text: str
    video_url: str
    group_link: str

class OrderSubmitSchema(BaseModel):
    user_id: str
    user_name: str
    product_id: int
    utr_proof: str

class OrderActionSchema(BaseModel):
    order_id: int

class SettingsSchema(BaseModel):
    upi_id: str
    qr_image: str
    theme_color: str
    enable_animation: bool
    admin_user: str
    admin_pass: str
    payment_note: str

class DeleteProductSchema(BaseModel):
    id: int

@app.get("/")
async def serve_store():
    return FileResponse("static/index.html")

@app.get("/admin")
async def serve_admin():
    return FileResponse("static/admin.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/admin/login")
async def admin_login(creds: LoginSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT admin_user, admin_pass FROM config WHERE id=1")
    row = c.fetchone()
    conn.close()
    if row and creds.username == row[0] and creds.password == row[1]:
        return {"status": "success", "token": "SPIDEY_SECURE_AUTH_8891"}
    return {"status": "error", "message": "Invalid Username or Password!"}

@app.get("/api/data")
async def get_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT upi_id, qr_image, theme_color, enable_animation, payment_note FROM config WHERE id=1")
    cfg = c.fetchone()
    c.execute("SELECT id, title, description, price, btn_text, video_url, group_link FROM products")
    products = [{"id": r[0], "title": r[1], "description": r[2], "price": r[3], "btn_text": r[4], "video_url": r[5], "group_link": r[6]} for r in c.fetchall()]
    conn.close()
    return {
        "config": {
            "upi_id": cfg[0], "qr_image": cfg[1], "theme_color": cfg[2], 
            "enable_animation": bool(cfg[3]), "payment_note": cfg[4] or ""
        }, 
        "products": products
    }

@app.post("/api/order/submit")
async def submit_order(order: OrderSubmitSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, price, group_link FROM products WHERE id=?", (order.product_id,))
    prod = c.fetchone()
    if not prod:
        conn.close()
        return {"status": "error", "message": "Product not found"}
    c.execute("""INSERT INTO orders (user_id, user_name, product_id, product_title, price, utr_proof, status, group_link)
                 VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)""",
              (order.user_id, order.user_name, order.product_id, prod[0], prod[1], order.utr_proof, prod[2]))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/user/orders/{user_id}")
async def get_user_orders(user_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, product_title, price, status, group_link FROM orders WHERE user_id=?", (user_id,))
    orders = [{"id": r[0], "title": r[1], "price": r[2], "status": r[3], "link": r[4] if r[3]=='APPROVED' else None} for r in c.fetchall()]
    conn.close()
    return {"orders": orders}

@app.get("/api/admin/dashboard")
async def get_dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(CAST(price AS INTEGER)) FROM orders WHERE status='APPROVED'")
    revenue = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(DISTINCT user_id) FROM orders")
    total_users = c.fetchone()[0] or 0
    c.execute("SELECT id, user_id, user_name, product_title, price, utr_proof FROM orders WHERE status='PENDING'")
    pending = [{"id": r[0], "user_id": r[1], "user_name": r[2], "title": r[3], "price": r[4], "utr": r[5]} for r in c.fetchall()]
    
    c.execute("SELECT id, title, description, price, btn_text, video_url, group_link FROM products")
    products = [{"id": r[0], "title": r[1], "description": r[2], "price": r[3], "btn_text": r[4], "video_url": r[5], "group_link": r[6]} for r in c.fetchall()]
    
    c.execute("SELECT admin_user, admin_pass, payment_note FROM config WHERE id=1")
    adm = c.fetchone()
    conn.close()
    return {
        "revenue": revenue, 
        "total_users": total_users, 
        "pending_orders": pending, 
        "products": products,
        "admin_user": adm[0], 
        "admin_pass": adm[1],
        "payment_note": adm[2] or ""
    }

@app.post("/api/admin/approve-order")
async def approve_order(action: OrderActionSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET status='APPROVED' WHERE id=?", (action.order_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/admin/reject-order")
async def reject_order(action: OrderActionSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET status='REJECTED' WHERE id=?", (action.order_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/admin/save-product")
async def save_product(product: ProductSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if product.id:
        c.execute("""UPDATE products SET title=?, description=?, price=?, btn_text=?, video_url=?, group_link=? 
                     WHERE id=?""",
                  (product.title, product.description, product.price, product.btn_text, product.video_url, product.group_link, product.id))
    else:
        c.execute("""INSERT INTO products (title, description, price, btn_text, video_url, group_link) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (product.title, product.description, product.price, product.btn_text, product.video_url, product.group_link))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/admin/delete-product")
async def delete_product(data: DeleteProductSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (data.id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/admin/update-settings")
async def update_settings(settings: SettingsSchema):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""UPDATE config SET upi_id=?, qr_image=?, theme_color=?, enable_animation=?, 
                 admin_user=?, admin_pass=?, payment_note=? WHERE id=1""",
              (settings.upi_id, settings.qr_image, settings.theme_color, int(settings.enable_animation), 
               settings.admin_user, settings.admin_pass, settings.payment_note))
    conn.commit()
    conn.close()
    return {"status": "success"}
    
