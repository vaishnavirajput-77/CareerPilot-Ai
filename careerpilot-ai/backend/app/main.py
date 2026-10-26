from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import CORS_ORIGINS
from .database import Base, engine, init_db
from . import models
from .api.routes import router

init_db(engine)


app = FastAPI(
    title="CareerPilot AI API",
    description="Explainable career intelligence and ML practice API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "careerpilot-ai-api"}

app.include_router(router)
