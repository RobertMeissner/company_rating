from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import blacklist, companies, jobs
from src.utils.settings import SERVICE_NAME

app = FastAPI(title=f"{SERVICE_NAME} API", version="1.0.0")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Docker frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(companies.router, prefix="/api", tags=["companies"])
app.include_router(blacklist.router, prefix="/api", tags=["blacklist"])


@app.get("/")
async def root():
    return {"message": f"{SERVICE_NAME} API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
