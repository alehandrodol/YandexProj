from fastapi import APIRouter

from .handlers import main_handlers, additional_handlers

routes = APIRouter()

routes.include_router(main_handlers.router, prefix="")
routes.include_router(additional_handlers.router, prefix="")
