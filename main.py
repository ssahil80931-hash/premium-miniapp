import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Live Database (In-Memory)
store_data = {
    "config": {
        "upi_id": "merchant@upi",
        "qr_image": "https://via.placeholder.com/250?text=Scan+QR+To+Pay",
        "theme_color": "#00ff9d",
        "enable_animation": True
    },
    "products": [
        {
            "id": 1,
            "title": "Demo Digital Course",
            "description": "Full HD Video Course with Lifetime Access",
            "price": "499",
            "btn_text": "Get Instant Access 🚀",
            "video_url": "https://www.w3schools.com/html/mov_bbb.mp4"
        }
    ]
}

class ProductSchema(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    price: str
    btn_text: str
    video_url: str

class SettingsSchema(BaseModel):
    upi_id: str
    qr_image: str
    theme_color: str
    enable_animation: bool

class DeleteSchema(BaseModel):
    id: int


# --- FRONTEND ROUTES ---
@app.get("/")
async def serve_store():
    return FileResponse("static/index.html")

@app.get("/admin")
async def serve_admin():
    return FileResponse("static/admin.html")

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- API ENDPOINTS ---
@app.get("/api/data")
async def get_data():
    return store_data

@app.post("/api/admin/save-product")
async def save_product(product: ProductSchema):
    new_p = product.dict()
    new_p['id'] = len(store_data['products']) + 1
    store_data['products'].append(new_p)
    return {"status": "success", "message": "Product Added Successfully!"}

@app.post("/api/admin/delete-product")
async def delete_product(data: DeleteSchema):
    store_data['products'] = [p for p in store_data['products'] if p['id'] != data.id]
    return {"status": "success", "message": "Product Deleted!"}

@app.post("/api/admin/update-settings")
async def update_settings(settings: SettingsSchema):
    store_data["config"] = settings.dict()
    return {"status": "success", "message": "Global Settings Updated!"}
    
