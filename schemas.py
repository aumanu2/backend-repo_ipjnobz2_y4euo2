"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal

# ---------------- Application-specific schemas ----------------

class Applicant(BaseModel):
    """
    Pendaftaran Mahasiswa Baru (collection: "applicant")
    """
    full_name: str = Field(..., min_length=3, max_length=120, description="Nama lengkap")
    email: EmailStr = Field(..., description="Email aktif")
    phone: str = Field(..., min_length=8, max_length=20, description="Nomor HP/WhatsApp")
    nik: str = Field(..., min_length=8, max_length=32, description="Nomor Induk Kependudukan")
    gender: Literal['Laki-laki', 'Perempuan'] = Field(..., description="Jenis kelamin")
    birth_place: str = Field(..., min_length=2, max_length=80, description="Tempat lahir")
    birth_date: str = Field(..., description="Tanggal lahir (YYYY-MM-DD)")
    address: str = Field(..., min_length=5, max_length=200, description="Alamat domisili")
    high_school: str = Field(..., min_length=3, max_length=120, description="Asal sekolah")
    graduation_year: int = Field(..., ge=2000, le=2100, description="Tahun lulus")
    study_program: str = Field(..., description="Program studi pilihan")
    study_degree: Literal['S1', 'S2', 'D3'] = Field(..., description="Jenjang pendidikan")
    intake: Literal['Ganjil', 'Genap'] = Field(..., description="Periode penerimaan")
    notes: Optional[str] = Field(None, max_length=300, description="Catatan tambahan")

# Example schemas left for reference (not used directly)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
