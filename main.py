import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Product as ProductSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image: Optional[str] = None
    rating: Optional[float] = None


def serialize_product(doc) -> dict:
    return {
        "id": str(doc.get("_id")),
        "title": doc.get("title"),
        "description": doc.get("description"),
        "price": float(doc.get("price", 0)),
        "category": doc.get("category", ""),
        "in_stock": bool(doc.get("in_stock", True)),
        "image": doc.get("image"),
        "rating": float(doc.get("rating", 0)) if doc.get("rating") is not None else None,
    }


@app.get("/")
def read_root():
    return {"message": "Shopping API running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.on_event("startup")
async def seed_products_on_startup():
    if db is None:
        return
    try:
        count = db["product"].count_documents({})
        if count == 0:
            sample_products = [
                {
                    "title": "EchoWave Smart Speaker",
                    "description": "Hands-free voice control with immersive 360° sound.",
                    "price": 79.99,
                    "category": "Electronics",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1518441902113-c1d4f5a9cfe0?q=80&w=1200&auto=format&fit=crop",
                    "rating": 4.6,
                },
                {
                    "title": "AeroFlex Running Shoes",
                    "description": "Breathable, ultra-light performance running shoes.",
                    "price": 129.0,
                    "category": "Fashion",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1200&auto=format&fit=crop",
                    "rating": 4.4,
                },
                {
                    "title": "LumaGlow Desk Lamp",
                    "description": "Minimal LED lamp with wireless charging base.",
                    "price": 59.5,
                    "category": "Home",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?q=80&w=1200&auto=format&fit=crop",
                    "rating": 4.7,
                },
                {
                    "title": "Nimbus Pro Backpack",
                    "description": "Water-resistant tech backpack with 16"" laptop sleeve.",
                    "price": 98.0,
                    "category": "Accessories",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1547949003-9792a18a2601?q=80&w=1200&auto=format&fit=crop",
                    "rating": 4.5,
                },
                {
                    "title": "BrewCraft Coffee Maker",
                    "description": "Programmable pour-over style coffee maker.",
                    "price": 149.99,
                    "category": "Kitchen",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1509460913899-35e6c0abf9b0?q=80&w=1200&auto=format&fit=crop",
                    "rating": 4.3,
                },
            ]
            for p in sample_products:
                try:
                    # validate with schema then insert
                    prod = ProductSchema(**{k: p[k] for k in [
                        "title", "description", "price", "category", "in_stock"
                    ] if k in p})
                    inserted_id = create_document("product", {**prod.model_dump(), "image": p.get("image"), "rating": p.get("rating")})
                except Exception:
                    continue
    except Exception:
        pass


@app.get("/api/products", response_model=List[ProductOut])
def list_products(q: Optional[str] = Query(default=None, description="Search query"),
                  category: Optional[str] = Query(default=None, description="Category filter"),
                  limit: int = Query(default=24, ge=1, le=100)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    filt = {}
    if q:
        # simple regex search on title/description
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filt["category"] = {"$regex": f"^{category}$", "$options": "i"}

    docs = get_documents("product", filt, limit)
    return [serialize_product(d) for d in docs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
