from mcp.server.lowlevel.server import Server as _McpServer
_original_init = _McpServer.__init__

def _patched_init(self, name, *args, **kwargs):
    if args:
        # Map the description positional argument to the instructions keyword argument
        kwargs.setdefault("instructions", args[0])
        kwargs.setdefault("version", "1.0.0")
    return _original_init(self, name, **kwargs)

_McpServer.__init__ = _patched_init




from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.config import settings
from app.database import engine, Base
from app.routes import auth, doctors, patients, appointments, prescriptions, records, reports, ai, cases, notifications
from fastapi_mcp import FastApiMCP
from app.utils.ai_runner import ALL_AGENT_TOOLS





# Automatically create tables for quick execution if needed
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Clinic Management System",
    description="Backend platform enabling clinics to manage users, doctors, patients, appointments, prescriptions, and medical records.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",          # Ваш локальный фронтенд
        "http://127.0.0.1:5173", ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount upload directory as static files (useful for downloading or viewing uploaded reports)
app.mount(f"/{settings.UPLOAD_DIR}", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(prescriptions.router)
app.include_router(records.router)
app.include_router(reports.router)
app.include_router(ai.router)
app.include_router(cases.router)
app.include_router(notifications.router)

@app.get("/")
def read_root():
    """Return the API's online status and link to its interactive documentation."""
    return {
        "status": "online",
        "message": "Welcome to the Clinic Management System API",
        "docs": "/docs"
    }





# Only the operations the role agents need are exposed as MCP tools (each agent is further limited to its own list). Each call is executed
# against the FastAPI app with the patient's forwarded JWT, so normal role checks apply.
mcp = FastApiMCP(
    app,
    name="SIRIUS Hospital MCP",
    include_operations=ALL_AGENT_TOOLS,
)
mcp.mount_sse(mount_path="/mcp")