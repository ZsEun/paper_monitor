from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, journals, digests, interests, credentials

# Load .env file for local development (no-op if file doesn't exist)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Academic Journal Monitor API")

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(journals.router, prefix="/api/journals", tags=["journals"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(interests.router, prefix="/api/user/interests", tags=["interests"])
app.include_router(credentials.router, prefix="/api/credentials", tags=["credentials"])

@app.get("/")
def read_root():
    return {"message": "Academic Journal Monitor API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
