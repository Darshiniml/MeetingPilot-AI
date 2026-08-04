from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

class ContactBase(BaseModel):
    display_name: str = Field(..., max_length=255)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    company: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=150)
    email: EmailStr | None = Field(None)
    phone: str | None = Field(None, max_length=50)
    linkedin_url: str | None = Field(None, max_length=512)
    is_favorite: bool = False
    notes: str | None = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    company: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=150)
    email: EmailStr | None = Field(None)
    phone: str | None = Field(None, max_length=50)
    linkedin_url: str | None = Field(None, max_length=512)
    is_favorite: bool | None = None
    notes: str | None = None

class ContactResponse(ContactBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ContactSearchRequest(BaseModel):
    query: str
    limit: int = 10

class ContactImportRequest(BaseModel):
    provider: str = Field("csv", description="Either 'csv' or 'google'")
    csv_content: str | None = Field(None, description="The raw CSV data content if importing via csv.")
