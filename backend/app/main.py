from fastapi import FastAPI

app = FastAPI(
    title="MeetingPilot AI API",
    version="1.0.0",
    description="Backend API for MeetingPilot AI"
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