from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.clusters import router as clusters_router
from api.health import router as health_router
from api.investigate import router as investigate_router
from core.config import settings
from core.kubeconfig import get_kubeconfig_status
from core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="AI Kubernetes Agent",
    description="On-demand Kubernetes troubleshooting with AI",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(clusters_router)
app.include_router(investigate_router)


@app.on_event("startup")
async def on_startup() -> None:
    kubeconfig = get_kubeconfig_status()
    if kubeconfig["configured"]:
        logger.info("Kubeconfig ready: {}", kubeconfig["path"])
    else:
        logger.warning("Kubeconfig not ready: {}", kubeconfig["error"])
    logger.info("AI Kubernetes Agent backend started")
