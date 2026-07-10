from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from model import Base
from routers.auth_router import router as auth_router
from routers.predict_router import router as predict_router

# ── Create all database tables ─────────────────────────────
Base.metadata.create_all(bind=engine)

# ── FastAPI app ────────────────────────────────────────────
app = FastAPI(
    title="DEPI Auth API",
    description="Authentication system with Register, Login, and Forgot Password.",
    version="1.0.0",
)

# ── CORS Middleware ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ────────────────────────────────────────
app.include_router(auth_router)
app.include_router(predict_router)


# ── Root health check ──────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "DEPI Auth API is running 🚀"}
