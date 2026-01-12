from fastapi import FastAPI

from app.api.v1.routes.mint import router as mint_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(mint_router, prefix="/v1", tags=["auth"])
    return app


app = create_app()
