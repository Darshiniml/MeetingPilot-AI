from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MeetingPilot AI API",
    version="1.0.0",
    description="Backend API for MeetingPilot AI"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "🚀 MeetingPilot AI Backend is Running!"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }