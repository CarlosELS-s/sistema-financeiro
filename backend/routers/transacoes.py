from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from decimal import Decimal

from database import get_db
from models import Transacao
from schemas import TransacaoCreate, TransacaoResponse


router = APIRouter(
    prefix="/api",
    tags=["Financeiro"]
)


@router.post("/transacoes", response_model=TransacaoResponse)
def criar_transacao(
    dados: TransacaoCreate,
    db: Session = Depends(get_db)
):
    nova_transacao = Transacao(
        descricao=dados.descricao.strip(),
        tipo=dados.tipo,
        categoria=dados.categoria.strip(),
        valor_centavos=int(dados.valor * 100),
        data=dados.data
    )

    db.add(nova_transacao)
    db.commit()
    db.refresh(nova_transacao)

    return nova_transacao


@router.get("/transacoes", response_model=list[TransacaoResponse])
def listar_transacoes(
    tipo: str | None = None,
    mes: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Transacao)

    if tipo:
        if tipo not in ["receita", "despesa"]:
            raise HTTPException(
                status_code=400,
                detail="Tipo de transação inválido."
            )

        query = query.filter(Transacao.tipo == tipo)

    if mes:
        try:
            ano, numero_mes = map(int, mes.split("-"))

            if numero_mes < 1 or numero_mes > 12:
                raise ValueError()

            inicio = date(ano, numero_mes, 1)

            if numero_mes == 12:
                fim = date(ano + 1, 1, 1)
            else:
                fim = date(ano, numero_mes + 1, 1)

            query = query.filter(
                Transacao.data >= inicio,
                Transacao.data < fim
            )

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Mês inválido. Utilize YYYY-MM."
            )

    return query.order_by(
        Transacao.data.desc(),
        Transacao.id.desc()
    ).all()


@router.delete("/transacoes/{transacao_id}")
def excluir_transacao(
    transacao_id: int,
    db: Session = Depends(get_db)
):
    transacao = db.query(Transacao).filter(
        Transacao.id == transacao_id
    ).first()

    if not transacao:
        raise HTTPException(
            status_code=404,
            detail="Transação não encontrada."
        )

    db.delete(transacao)
    db.commit()

    return {"message": "Transação excluída com sucesso."}


@router.get("/dashboard")
def dashboard(
    mes: str | None = None,
    db: Session = Depends(get_db)
):
    if mes is None:
        mes = date.today().strftime("%Y-%m")

    try:
        ano, numero_mes = map(int, mes.split("-"))

        if numero_mes < 1 or numero_mes > 12:
            raise ValueError()

        inicio = date(ano, numero_mes, 1)

        if numero_mes == 12:
            fim = date(ano + 1, 1, 1)
        else:
            fim = date(ano, numero_mes + 1, 1)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Mês inválido. Utilize YYYY-MM."
        )

    def somar(tipo, data_inicio=None, data_fim=None):
        query = db.query(
            func.coalesce(
                func.sum(Transacao.valor_centavos), 0
            )
        ).filter(Transacao.tipo == tipo)

        if data_inicio:
            query = query.filter(Transacao.data >= data_inicio)

        if data_fim:
            query = query.filter(Transacao.data < data_fim)

        return int(query.scalar() or 0)

    receitas_mes = somar("receita", inicio, fim)
    despesas_mes = somar("despesa", inicio, fim)

    receitas_total = somar("receita")
    despesas_total = somar("despesa")

    saldo_total = receitas_total - despesas_total

    despesas_categoria = db.query(
        Transacao.categoria,
        func.sum(Transacao.valor_centavos)
    ).filter(
        Transacao.tipo == "despesa",
        Transacao.data >= inicio,
        Transacao.data < fim
    ).group_by(
        Transacao.categoria
    ).all()

    ultimas = db.query(Transacao).order_by(
        Transacao.data.desc(),
        Transacao.id.desc()
    ).limit(5).all()

    return {
        "mes": mes,
        "saldo_total": saldo_total / 100,
        "receitas_total": receitas_total / 100,
        "despesas_total": despesas_total / 100,
        "receitas_mes": receitas_mes / 100,
        "despesas_mes": despesas_mes / 100,
        "saldo_mes": (receitas_mes - despesas_mes) / 100,
        "despesas_categoria": [
            {
                "categoria": categoria,
                "valor": int(valor or 0) / 100
            }
            for categoria, valor in despesas_categoria
        ],
        "ultimas_transacoes": [
            {
                "id": t.id,
                "descricao": t.descricao,
                "tipo": t.tipo,
                "categoria": t.categoria,
                "valor": t.valor,
                "data": t.data.isoformat()
            }
            for t in ultimas
        ]
    }