import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Applicant

app = FastAPI(title="PMB UMB Jakarta API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API Pendaftaran Mahasiswa Baru UMB Jakarta"}

# Helper to convert Mongo docs
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


def serialize_doc(doc):
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    # Convert datetime to isoformat if exists
    for k in ["created_at", "updated_at"]:
        if k in doc and hasattr(doc[k], "isoformat"):
            doc[k] = doc[k].isoformat()
    return doc

@app.get("/test")
def test_database():
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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
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

    return response

# ---------------- PMB Endpoints ----------------

@app.post("/api/applicants", status_code=201)
async def create_applicant(payload: Applicant):
    try:
        inserted_id = create_document("applicant", payload)
        return {"id": inserted_id, "message": "Pendaftaran berhasil diterima"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applicants")
async def list_applicants(limit: Optional[int] = 50):
    try:
        docs = get_documents("applicant", limit=limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
