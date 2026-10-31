
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base

# Importar os modelos para o SQLAlchemy reconhecer todas as tabelas
from models import (
    Transacao,
    ContaFixa,
    ContaMensal,
    CartaoCredito,
    FaturaCartao,
    CompraCartao,
)

from routers.transacoes import router as transacoes_router
from routers.contas_fixas import router as contas_fixas_router
from routers.cartoes import router as cartoes_router


# Criar tabelas que ainda não existem, preservando os dados atuais
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Sistema Financeiro",
    description="API de controle financeiro pessoal",
    version="1.0.0"
)


# =====================================
# ROTAS DA API
# =====================================

app.include_router(transacoes_router)
app.include_router(contas_fixas_router)
app.include_router(cartoes_router)


# =====================================
# FRONTEND
# =====================================

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

@app.get("/cartoes")
def pagina_cartoes():
    return FileResponse(FRONTEND_DIR / "cartoes.html")

@app.get("/contas-fixas", include_in_schema=False)
def pagina_contas_fixas():
    return FileResponse(FRONTEND_DIR / "contas-fixas.html")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api")
def verificar_api():
    return {
        "status": "online",
        "mensagem": "Sistema Financeiro funcionando!"
    }
