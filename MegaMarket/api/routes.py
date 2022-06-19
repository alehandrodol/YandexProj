from fastapi import APIRouter

from .handlers import main_handlers

routes = APIRouter()

routes.include_router(main_handlers.router, prefix="")
