from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.api_keys import router as keys_router
from app.api.v1.routes.mint import router as mint_router

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI()

    # This is added as Broswer send OPTION prior
    # essentially asking for privilege.
    # Middleware tells the browser they have privilege
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],  # includes Authorization
    )
    app.include_router(mint_router, prefix="/v1", tags=["auth"])
    app.include_router(keys_router, prefix="/v1", tags=["keys"])

    return app


app = create_app()
