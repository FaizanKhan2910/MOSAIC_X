from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.api.routes_data import router as data_router
from backend.app.api.routes_discovery import router as discovery_router
from backend.app.api.routes_context import router as context_router
from backend.app.api.routes_simulation import router as simulation_router
from backend.app.api.routes_experiments import router as experiments_router
from backend.app.api.routes_privacy import router as privacy_router
from backend.app.api.routes_demo import router as demo_router

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "NEXORA: A Privacy-First Multimodal AI System for Personal Data Fusion, "
        "Behavioural Pattern Discovery, Uncertainty-Aware Reasoning, Predictive "
        "What-If Simulation and Adaptive Personal Experimentation."
    ),
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(data_router, prefix=settings.API_PREFIX)
app.include_router(discovery_router, prefix=settings.API_PREFIX)
app.include_router(context_router, prefix=settings.API_PREFIX)
app.include_router(simulation_router, prefix=settings.API_PREFIX)
app.include_router(experiments_router, prefix=settings.API_PREFIX)
app.include_router(privacy_router, prefix=settings.API_PREFIX)
app.include_router(demo_router, prefix=settings.API_PREFIX)

@app.get("/")
def read_root():
    return {
        "project": "NEXORA",
        "tagline": "Beyond Tracking. Beyond Knowing. Discovering You.",
        "status": "online",
        "core_loop": ["OBSERVE", "DISCOVER", "QUESTION", "SIMULATE", "EXPERIMENT", "LEARN"],
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "NEXORA Intelligence Engine"}
