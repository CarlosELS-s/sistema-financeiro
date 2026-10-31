
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CartaoCredito,
    CompraCartao,
    FaturaCartao,
    Transacao,
)
from schemas import (
    CartaoCreditoCreate,
    CartaoCreditoUpdate,
    CartaoCreditoResponse,
    CompraCartaoCreate,
    CompraCartaoResponse,
    FaturaCartaoResponse,
    FaturaCartaoPagar,
)


router = APIRouter(
    prefix="/api/cartoes",
    tags=["Cartões de crédito"]
)


def para_centavos(valor: Decimal) -> int:
    return int(
        (valor * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def ultimo_dia(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]


def data_segura(ano: int, mes: int, dia: int) -> date:
    return date(ano, mes, min(dia, ultimo_dia(ano, mes)))


def calcular_periodo(cartao: CartaoCredito, data_compra: date):
    """
    Compras feitas até o dia de fechamento entram
    na fatura que fecha naquele mês.

    Compras posteriores entram na próxima fatura.
    """

    if data_compra.day <= cartao.dia_fechamento:
        ano = data_compra.year
        mes = data_compra.month
    else:
        if data_compra.month == 12:
            ano = data_compra.year + 1
            mes = 1
        else:
            ano = data_compra.year
            mes = data_compra.month + 1

    vencimento_mes = mes + 1
    vencimento_ano = ano

    if vencimento_mes > 12:
        vencimento_mes = 1
        vencimento_ano += 1

    vencimento = data_segura(
        vencimento_ano,
        vencimento_mes,
        cartao.dia_vencimento
    )

    return ano, mes, vencimento


def obter_ou_criar_fatura(
    db: Session,
    cartao: CartaoCredito,
    data_compra: date
):
    ano, mes, vencimento = calcular_periodo(
        cartao,
        data_compra
    )

    fatura = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao.id,
        FaturaCartao.ano == ano,
        FaturaCartao.mes == mes
    ).first()

    if not fatura:
        fatura = FaturaCartao(
            cartao_id=cartao.id,
            ano=ano,
            mes=mes,
            vencimento=vencimento,
            status="aberta"
        )

        db.add(fatura)
        db.flush()

    return fatura


def total_fatura(db: Session, fatura_id: int) -> int:
    compras = db.query(CompraCartao).filter(
        CompraCartao.fatura_id == fatura_id
    ).all()

    return sum(compra.valor_centavos for compra in compras)


def total_utilizado(db: Session, cartao_id: int) -> int:
    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao_id,
        FaturaCartao.status != "paga"
    ).all()

    return sum(
        total_fatura(db, fatura.id)
        for fatura in faturas
    )


# =====================================
# CADASTRAR CARTÃO
# =====================================

@router.post("", response_model=CartaoCreditoResponse)
def criar_cartao(
    dados: CartaoCreditoCreate,
    db: Session = Depends(get_db)
):
    cartao = CartaoCredito(
        nome=dados.nome,
        banco=dados.banco,
        limite_centavos=para_centavos(dados.limite),
        dia_fechamento=dados.dia_fechamento,
        dia_vencimento=dados.dia_vencimento
    )

    db.add(cartao)
    db.commit()
    db.refresh(cartao)

    return cartao


# =====================================
# LISTAR CARTÕES
# =====================================

@router.get("")
def listar_cartoes(db: Session = Depends(get_db)):
    cartoes = db.query(CartaoCredito).filter(
        CartaoCredito.ativo == True
    ).all()

    resultado = []

    for cartao in cartoes:
        utilizado = total_utilizado(db, cartao.id)

        resultado.append({
            "id": cartao.id,
            "nome": cartao.nome,
            "banco": cartao.banco,
            "limite_centavos": cartao.limite_centavos,
            "utilizado_centavos": utilizado,
            "disponivel_centavos": max(
                0,
                cartao.limite_centavos - utilizado
            ),
            "dia_fechamento": cartao.dia_fechamento,
            "dia_vencimento": cartao.dia_vencimento
        })

    return resultado


# =====================================
# EDITAR CARTÃO
# =====================================

@router.put("/{cartao_id}", response_model=CartaoCreditoResponse)
def atualizar_cartao(
    cartao_id: int,
    dados: CartaoCreditoUpdate,
    db: Session = Depends(get_db)
):
    cartao = db.query(CartaoCredito).filter(
        CartaoCredito.id == cartao_id
    ).first()

    if not cartao:
        raise HTTPException(404, "Cartão não encontrado.")

    atualizacoes = dados.model_dump(exclude_unset=True)

    for campo, valor in atualizacoes.items():
        if campo == "limite":
            cartao.limite_centavos = para_centavos(valor)
        else:
            setattr(cartao, campo, valor)

    db.commit()
    db.refresh(cartao)

    return cartao


# =====================================
# EXCLUIR CARTÃO
# =====================================

@router.delete("/{cartao_id}")
def excluir_cartao(
    cartao_id: int,
    db: Session = Depends(get_db)
):
    cartao = db.query(CartaoCredito).filter(
        CartaoCredito.id == cartao_id
    ).first()

    if not cartao:
        raise HTTPException(404, "Cartão não encontrado.")

    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao_id
    ).all()

    for fatura in faturas:
        if fatura.status == "paga":
            raise HTTPException(
                400,
                "Não é possível excluir um cartão com faturas pagas."
            )

    for fatura in faturas:
        db.query(CompraCartao).filter(
            CompraCartao.fatura_id == fatura.id
        ).delete(synchronize_session=False)

    db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao_id
    ).delete(synchronize_session=False)

    db.delete(cartao)
    db.commit()

    return {"mensagem": "Cartão excluído com sucesso."}


# =====================================
# REGISTRAR COMPRA
# =====================================

@router.post("/{cartao_id}/compras")
def registrar_compra(
    cartao_id: int,
    dados: CompraCartaoCreate,
    db: Session = Depends(get_db)
):
    cartao = db.query(CartaoCredito).filter(
        CartaoCredito.id == cartao_id,
        CartaoCredito.ativo == True
    ).first()

    if not cartao:
        raise HTTPException(404, "Cartão não encontrado.")

    fatura = obter_ou_criar_fatura(
        db,
        cartao,
        dados.data
    )

    if fatura.status == "paga":
        raise HTTPException(
            400,
            "Esta fatura já foi paga."
        )

    valor_centavos = para_centavos(dados.valor)

    utilizado = total_utilizado(db, cartao.id)

    if utilizado + valor_centavos > cartao.limite_centavos:
        raise HTTPException(
            400,
            "Esta compra ultrapassa o limite disponível do cartão."
        )

    compra = CompraCartao(
        fatura_id=fatura.id,
        descricao=dados.descricao,
        categoria=dados.categoria,
        valor_centavos=valor_centavos,
        data=dados.data
    )

    db.add(compra)
    db.commit()
    db.refresh(compra)

    return {
        "mensagem": "Compra registrada com sucesso.",
        "compra": {
            "id": compra.id,
            "fatura_id": compra.fatura_id,
            "descricao": compra.descricao,
            "categoria": compra.categoria,
            "valor_centavos": compra.valor_centavos,
            "data": compra.data
        }
    }


# =====================================
# LISTAR FATURAS
# =====================================

@router.get("/{cartao_id}/faturas")
def listar_faturas(
    cartao_id: int,
    db: Session = Depends(get_db)
):
    cartao = db.query(CartaoCredito).filter(
        CartaoCredito.id == cartao_id
    ).first()

    if not cartao:
        raise HTTPException(404, "Cartão não encontrado.")

    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao_id
    ).order_by(
        FaturaCartao.ano.desc(),
        FaturaCartao.mes.desc()
    ).all()

    resultado = []

    for fatura in faturas:
        compras = db.query(CompraCartao).filter(
            CompraCartao.fatura_id == fatura.id
        ).order_by(CompraCartao.data.desc()).all()

        resultado.append({
            "id": fatura.id,
            "cartao_id": fatura.cartao_id,
            "ano": fatura.ano,
            "mes": fatura.mes,
            "vencimento": fatura.vencimento,
            "status": fatura.status,
            "total_centavos": total_fatura(db, fatura.id),
            "transacao_id": fatura.transacao_id,
            "data_pagamento": fatura.data_pagamento,
            "compras": [
                {
                    "id": compra.id,
                    "fatura_id": compra.fatura_id,
                    "descricao": compra.descricao,
                    "categoria": compra.categoria,
                    "valor_centavos": compra.valor_centavos,
                    "data": compra.data
                }
                for compra in compras
            ]
        })

    return resultado


# =====================================
# PAGAR FATURA INTEIRA
# =====================================

@router.post("/faturas/{fatura_id}/pagar")
def pagar_fatura(
    fatura_id: int,
    dados: FaturaCartaoPagar,
    db: Session = Depends(get_db)
):
    fatura = db.query(FaturaCartao).filter(
        FaturaCartao.id == fatura_id
    ).first()

    if not fatura:
        raise HTTPException(404, "Fatura não encontrada.")

    if fatura.status == "paga":
        raise HTTPException(
            400,
            "Esta fatura já foi paga."
        )

    cartao = db.query(CartaoCredito).filter(
        CartaoCredito.id == fatura.cartao_id
    ).first()

    total = total_fatura(db, fatura.id)

    if total <= 0:
        raise HTTPException(
            400,
            "Não é possível pagar uma fatura sem compras."
        )

    transacao = Transacao(
        descricao=f"Fatura do cartão {cartao.nome}",
        tipo="despesa",
        categoria="Cartão de crédito",
        valor_centavos=total,
        data=dados.data_pagamento
    )

    db.add(transacao)
    db.flush()

    fatura.status = "paga"
    fatura.transacao_id = transacao.id
    fatura.data_pagamento = dados.data_pagamento

    db.commit()

    return {
        "mensagem": "Fatura paga integralmente.",
        "valor_pago_centavos": total,
        "transacao_id": transacao.id
    }
