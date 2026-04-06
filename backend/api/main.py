import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import alerts, auth, health, prices, products, webhooks

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Price Tracker API",
    description="Track e-commerce product prices and get Telegram alerts when prices drop.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(prices.router, prefix="/prices", tags=["Prices"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Price Tracker API starting up...")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Price Tracker API shutting down...")
