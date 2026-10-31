from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base
from routers.transacoes import router as transacoes_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Financeiro",
    description="API de controle financeiro pessoal",
    version="1.0.0"
)

app.include_router(transacoes_router)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/css",
    StaticFiles(directory=FRONTEND_DIR / "css"),
    name="css"
)

app.mount(
    "/js",
    StaticFiles(directory=FRONTEND_DIR / "js"),
    name="js"
)


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/api")
def verificar_api():
    return {
        "status": "online",
        "mensagem": "Sistema Financeiro funcionando!"
    }