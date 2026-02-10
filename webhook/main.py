import uvicorn
from app import create_app

app = create_app()

if __name__ == "__main__":
    print("Webhook-Server wird gestartet auf Port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
