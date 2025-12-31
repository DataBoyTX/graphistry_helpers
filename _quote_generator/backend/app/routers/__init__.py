"""API routers package."""
from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.dashboard import router as dashboard_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.quotes import router as quotes_router
from app.routers.users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "customers_router",
    "products_router",
    "quotes_router",
    "orders_router",
    "dashboard_router",
]
