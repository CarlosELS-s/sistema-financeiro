
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base####

# Importar todos os modelos
from models import (
    Usuario,
    Transacao,
    ContaFixa,
    ContaMensal,
    CartaoCredito,
    FaturaCartao,
    CompraCartao,
    Orcamento,
)

# Importar routers
from routers.transacoes import router as transacoes_router
from routers.contas_fixas import router as contas_fixas_router
from routers.cartoes import router as cartoes_router
from routers.autenticacao import router as autenticacao_router
####

# =====================================
# CRIAR TABELAS DO BANCO
# =====================================

Base.metadata.create_all(bind=engine)


# =====================================
# CONFIGURAÇÃO DA API
# =====================================

app = FastAPI(
    title="Sistema Financeiro",
    description="API de controle financeiro pessoal",
    version="1.0.0"
)


# =====================================
# CONFIGURAÇÃO DO FRONTEND
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# =====================================
# ROTAS DA API
# =====================================

app.include_router(transacoes_router)
app.include_router(contas_fixas_router)
app.include_router(cartoes_router)
app.include_router(autenticacao_router)


# =====================================
# ARQUIVOS ESTÁTICOS
# =====================================

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


# =====================================
# DIAGNÓSTICO DO AUTH.JS
# =====================================

@app.get("/teste-arquivo-js")
def teste_arquivo_js():
    arquivo = FRONTEND_DIR / "js" / "auth.js"

    return {
        "base_dir": str(BASE_DIR),
        "frontend_dir": str(FRONTEND_DIR),
        "caminho_auth_js": str(arquivo.resolve()),
        "existe": arquivo.exists(),
        "tamanho": arquivo.stat().st_size if arquivo.exists() else 0,
        "possui_funcao_visitante": (
            "async function entrarComoVisitante" in arquivo.read_text(
                encoding="utf-8"
            )
            if arquivo.exists()
            else False
        )
    }


# =====================================
# PÁGINAS
# =====================================

@app.get("/recuperar-senha", include_in_schema=False)
def pagina_recuperar_senha():
    return FileResponse(FRONTEND_DIR / "recuperar-senha.html")


@app.get("/favicon1.png", include_in_schema=False)
def favicon():
    return FileResponse(FRONTEND_DIR / "favicon1.png")


@app.get("/login", include_in_schema=False)
def pagina_login():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/cadastro", include_in_schema=False)
def pagina_cadastro():
    return FileResponse(FRONTEND_DIR / "cadastro.html")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/dashboard", include_in_schema=False)
def pagina_dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/cartoes", include_in_schema=False)
def pagina_cartoes():
    return FileResponse(FRONTEND_DIR / "cartoes.html")


@app.get("/contas-fixas", include_in_schema=False)
def pagina_contas_fixas():
    return FileResponse(FRONTEND_DIR / "contas-fixas.html")


# =====================================
# VERIFICAR API
# =====================================

@app.get("/api")
def verificar_api():
    return {
        "status": "online",
        "mensagem": "Sistema Financeiro funcionando!"
    }


# =====================================
# EXECUÇÃO
# =====================================

# Para executar localmente:
# python -m uvicorn main:app --reload
