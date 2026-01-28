from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, tarot, debug, system, stripe, admin
from app.config import settings
import os
import logging
import sys
from datetime import datetime

# Setup Logging
def setup_logging():
    # Create logs directory
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Log filename with date
    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"{current_date}.log")
    
    # Configure logging
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    stream_handler = logging.StreamHandler(sys.stdout)
    
    # Define format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler],
        force=True
    )
    
    # Ensure uvicorn loggers also write to file
    # uvicorn.error and uvicorn.access are the main loggers.
    # Attaching to "uvicorn" might cause duplication if children propagate.
    for logger_name in ["uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.addHandler(file_handler)
    
    logging.info(f"Logging initialized. Writing to {log_file}")

setup_logging()

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Determine if running on HTTPS
is_https = settings.API_BASE_URL and settings.API_BASE_URL.startswith("https://")

# Middleware Stack (constructed in reverse order of addition)
# We want: ProxyHeaders -> Session -> CORS -> App
# So we add: CORS, then Session, then ProxyHeaders

# CORS (Inner-most of these three, but handles OPTIONS requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY, 
    https_only=is_https, 
    same_site="none" if is_https else "lax",
    domain=".mentobe.co" if is_https else None
)

# Proxy Headers Middleware (Outer-most, ensures scheme is correct for Session)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(tarot.router, prefix="/api")
app.include_router(debug.router, prefix="/api")
app.include_router(system.router, prefix="/api") # /api/init
app.include_router(stripe.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# Static files (Web Interface)
# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/health")
async def health():
    return {"status": "ok"}
