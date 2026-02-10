from fastapi import FastAPI
from app.api import router


def create_app() -> FastAPI:
    application = FastAPI(title="WhatsApp Chatbot MVP")
    application.include_router(router)
    return application
