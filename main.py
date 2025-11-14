import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Applicant, User as UserSchema, LoginRequest, TokenResponse, MeResponse

# ---------------- App & CORS ----------------
app = FastAPI(title="PMB UMB Jakarta API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Security / Auth ----------------
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkeychange")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


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
    for k in ["created_at", "updated_at"]:
        if k in doc and hasattr(doc[k], "isoformat"):
            doc[k] = doc[k].isoformat()
    return doc


# ---------------- Root & Health ----------------
@app.get("/")
def read_root():
    return {"message": "API Pendaftaran Mahasiswa Baru UMB Jakarta"}


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


# ---------------- Auth Endpoints ----------------
@app.post("/auth/register", response_model=MeResponse, status_code=201)
def register(user: UserSchema):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = db["user"].find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    data = user.model_dump()
    data["password"] = hash_password(data["password"])
    data["created_at"] = datetime.now(timezone.utc)
    data["updated_at"] = datetime.now(timezone.utc)

    result = db["user"].insert_one(data)
    return MeResponse(id=str(result.inserted_id), full_name=user.full_name, email=user.email, role=user.role)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    user = db["user"].find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    token = create_access_token({"sub": str(user["_id"]), "email": user["email"], "role": user.get("role", "applicant")})
    return TokenResponse(access_token=token)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    credentials_exception = HTTPException(status_code=401, detail="Tidak terautentikasi")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db["user"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise credentials_exception
    return user


@app.get("/auth/me", response_model=MeResponse)
def me(current_user: dict = Depends(get_current_user)):
    return MeResponse(id=str(current_user["_id"]), full_name=current_user.get("full_name"), email=current_user.get("email"), role=current_user.get("role", "applicant"))


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


# Admin-protected listing (optional)
@app.get("/admin/applicants")
async def admin_list_applicants(limit: Optional[int] = 100, current_user: dict = Depends(get_current_user)):
    role = current_user.get("role", "applicant")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak")
    try:
        docs = get_documents("applicant", limit=limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
