from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

db = {"products": [], "orders": [], "config": {"upi_id": "yourname@upi", "payment_note": "Scan QR"}}

@app.get("/")
async def read_index():
    with open("static/index.html", "r") as f: return HTMLResponse(content=f.read())

@app.get("/admin")
async def read_admin():
    with open("static/admin.html", "r") as f: return HTMLResponse(content=f.read())

@app.post("/api/admin/login")
async def login(req: Request):
    data = await req.json()
    if data.get("username") == "admin" and data.get("password") == "admin123":
        return {"status": "success"}
    return {"status": "error"}, 401

@app.get("/api/admin/dashboard")
async def dashboard():
    return db

@app.post("/api/admin/save-product")
async def save_product(req: Request):
    data = await req.json()
    db["products"].append(data) # इसे और बेहतर बाद में कर लेंगे
    return {"status": "success"}

@app.post("/api/order/submit")
async def submit(req: Request):
    data = await req.json()
    db["orders"].append(data)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
