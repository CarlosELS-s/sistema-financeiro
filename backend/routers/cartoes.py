
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import (
    Usuario,
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
    FaturaCartaoPagar,
)
from auth import get_usuario_atual


router = APIRouter(
    prefix="/api/cartoes",
    tags=["Cartões de crédito"]
)


# =====================================
# FUNÇÕES AUXILIARES
# =====================================

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
    return date(
        ano,
        mes,
        min(dia, ultimo_dia(ano, mes))
    )


def calcular_periodo(
    cartao: CartaoCredito,
    data_compra: date
):
    """
    Antes do fechamento:
        entra na fatura do mês atual.

    No dia do fechamento ou depois:
        entra na fatura do próximo mês.

    O vencimento acontece no mês seguinte
    ao mês da fatura.
    """

    if data_compra.day < cartao.dia_fechamento:
        ano = data_compra.year
        mes = data_compra.month
    else:
        ano = data_compra.year
        mes = data_compra.month + 1

        if mes > 12:
            mes = 1
            ano += 1

    ano_vencimento = ano
    mes_vencimento = mes + 1

    if mes_vencimento > 12:
        mes_vencimento = 1
        ano_vencimento += 1

    vencimento = data_segura(
        ano_vencimento,
        mes_vencimento,
        cartao.dia_vencimento
    )

    return ano, mes, vencimento


def obter_ou_criar_fatura(
    db: Session,
    cartao: CartaoCredito,
    ano: int,
    mes: int
):
    fatura = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao.id,
        FaturaCartao.ano == ano,
        FaturaCartao.mes == mes
    ).first()

    if fatura:
        return fatura

    ano_vencimento = ano
    mes_vencimento = mes + 1

    if mes_vencimento > 12:
        mes_vencimento = 1
        ano_vencimento += 1

    vencimento = data_segura(
        ano_vencimento,
        mes_vencimento,
        cartao.dia_vencimento
    )

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


def total_fatura(
    db: Session,
    fatura_id: int
) -> int:
    return int(
        db.query(
            func.coalesce(
                func.sum(CompraCartao.valor_centavos),
                0
            )
        ).filter(
            CompraCartao.fatura_id == fatura_id
        ).scalar() or 0
    )


def total_utilizado(
    db: Session,
    cartao_id: int
) -> int:
    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao_id,
        FaturaCartao.status != "paga"
    ).all()

    return sum(
        total_fatura(db, fatura.id)
        for fatura in faturas
    )


def buscar_cartao_usuario(
    db: Session,
    cartao_id: int,
    usuario_id: int,
    exigir_ativo: bool = False
):
    consulta = db.query(CartaoCredito).filter(
        CartaoCredito.id == cartao_id,
        CartaoCredito.usuario_id == usuario_id
    )

    if exigir_ativo:
        consulta = consulta.filter(
            CartaoCredito.ativo == True
        )

    return consulta.first()


# =====================================
# REGISTRAR COMPRA PARCELADA
# =====================================

def registrar_compra_parcelada(
    db: Session,
    cartao: CartaoCredito,
    descricao: str,
    categoria: str,
    valor_centavos: int,
    data_compra: date,
    parcelas: int
):
    if parcelas < 1 or parcelas > 60:
        raise HTTPException(
            400,
            "A quantidade de parcelas deve estar entre 1 e 60."
        )

    utilizado = total_utilizado(
        db,
        cartao.id
    )

    if utilizado + valor_centavos > cartao.limite_centavos:
        raise HTTPException(
            400,
            "Esta compra ultrapassa o limite disponível do cartão."
        )

    ano, mes, _ = calcular_periodo(
        cartao,
        data_compra
    )

    valor_base = valor_centavos // parcelas
    resto = valor_centavos % parcelas

    compras = []

    for numero in range(1, parcelas + 1):

        valor_parcela = valor_base

        if numero <= resto:
            valor_parcela += 1

        fatura = obter_ou_criar_fatura(
            db,
            cartao,
            ano,
            mes
        )

        if fatura.status == "paga":
            raise HTTPException(
                400,
                f"A fatura de {mes:02d}/{ano} já foi paga."
            )

        compra = CompraCartao(
            fatura_id=fatura.id,
            descricao=(
                f"{descricao} ({numero}/{parcelas})"
                if parcelas > 1
                else descricao
            ),
            categoria=categoria,
            valor_centavos=valor_parcela,
            data=data_compra
        )

        db.add(compra)
        compras.append(compra)

        mes += 1

        if mes > 12:
            mes = 1
            ano += 1

    db.flush()

    return compras


# =====================================
# CADASTRAR CARTÃO
# =====================================

@router.post(
    "",
    response_model=CartaoCreditoResponse
)
def criar_cartao(
    dados: CartaoCreditoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    cartao = CartaoCredito(
        usuario_id=usuario.id,
        nome=dados.nome.strip(),
        banco=dados.banco.strip() if dados.banco else None,
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
def listar_cartoes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    cartoes = db.query(CartaoCredito).filter(
        CartaoCredito.usuario_id == usuario.id,
        CartaoCredito.ativo == True
    ).order_by(
        CartaoCredito.id.desc()
    ).all()

    resultado = []

    for cartao in cartoes:
        utilizado = total_utilizado(
            db,
            cartao.id
        )

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

@router.put(
    "/{cartao_id}",
    response_model=CartaoCreditoResponse
)
def atualizar_cartao(
    cartao_id: int,
    dados: CartaoCreditoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    cartao = buscar_cartao_usuario(
        db,
        cartao_id,
        usuario.id,
        exigir_ativo=True
    )

    if not cartao:
        raise HTTPException(
            404,
            "Cartão não encontrado."
        )

    atualizacoes = dados.model_dump(
        exclude_unset=True
    )

    for campo, valor in atualizacoes.items():

        if campo == "limite":
            novo_limite = para_centavos(valor)

            utilizado = total_utilizado(
                db,
                cartao.id
            )

            if novo_limite < utilizado:
                raise HTTPException(
                    400,
                    "O novo limite não pode ser menor que o valor já utilizado."
                )

            cartao.limite_centavos = novo_limite

        elif campo == "nome":
            cartao.nome = valor.strip()

        elif campo == "banco":
            cartao.banco = valor.strip() if valor else None

        else:
            setattr(cartao, campo, valor)

    db.commit()
    db.refresh(cartao)

    return cartao


# =====================================
# DESATIVAR CARTÃO
# =====================================

@router.delete("/{cartao_id}")
def excluir_cartao(
    cartao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    cartao = buscar_cartao_usuario(
        db,
        cartao_id,
        usuario.id,
        exigir_ativo=True
    )

    if not cartao:
        raise HTTPException(
            404,
            "Cartão não encontrado."
        )

    cartao.ativo = False

    db.commit()

    return {
        "mensagem": "Cartão desativado. O histórico foi preservado."
    }


# =====================================
# REGISTRAR COMPRA
# =====================================

@router.post("/{cartao_id}/compras")
def registrar_compra(
    cartao_id: int,
    dados: CompraCartaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    cartao = buscar_cartao_usuario(
        db,
        cartao_id,
        usuario.id,
        exigir_ativo=True
    )

    if not cartao:
        raise HTTPException(
            404,
            "Cartão não encontrado ou inativo."
        )

    try:
        compras = registrar_compra_parcelada(
            db=db,
            cartao=cartao,
            descricao=dados.descricao.strip(),
            categoria=dados.categoria.strip(),
            valor_centavos=para_centavos(dados.valor),
            data_compra=dados.data,
            parcelas=dados.parcelas
        )

        db.commit()

        return {
            "mensagem": "Compra registrada com sucesso.",
            "parcelas": len(compras),
            "valor_total_centavos": para_centavos(
                dados.valor
            )
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# LISTAR FATURAS
# =====================================

@router.get("/{cartao_id}/faturas")
def listar_faturas(
    cartao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    cartao = buscar_cartao_usuario(
        db,
        cartao_id,
        usuario.id
    )

    if not cartao:
        raise HTTPException(
            404,
            "Cartão não encontrado."
        )

    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao.id
    ).order_by(
        FaturaCartao.ano.desc(),
        FaturaCartao.mes.desc()
    ).all()

    resultado = []

    for fatura in faturas:

        compras = db.query(CompraCartao).filter(
            CompraCartao.fatura_id == fatura.id
        ).order_by(
            CompraCartao.data.desc(),
            CompraCartao.id.desc()
        ).all()

        resultado.append({
            "id": fatura.id,
            "cartao_id": fatura.cartao_id,
            "ano": fatura.ano,
            "mes": fatura.mes,
            "vencimento": fatura.vencimento,
            "status": fatura.status,
            "total_centavos": total_fatura(
                db,
                fatura.id
            ),
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
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    # A fatura só pode ser acessada se pertencer
    # a um cartão do usuário autenticado.

    fatura = db.query(FaturaCartao).join(
        CartaoCredito,
        CartaoCredito.id == FaturaCartao.cartao_id
    ).filter(
        FaturaCartao.id == fatura_id,
        CartaoCredito.usuario_id == usuario.id
    ).first()

    if not fatura:
        raise HTTPException(
            404,
            "Fatura não encontrada."
        )

    if fatura.status == "paga":
        raise HTTPException(
            400,
            "Esta fatura já foi paga."
        )

    cartao = db.query(CartaoCredito).filter(
        CartaoCredito.id == fatura.cartao_id,
        CartaoCredito.usuario_id == usuario.id
    ).first()

    if not cartao:
        raise HTTPException(
            404,
            "Cartão não encontrado."
        )

    total = total_fatura(
        db,
        fatura.id
    )

    if total <= 0:
        raise HTTPException(
            400,
            "Não é possível pagar uma fatura sem compras."
        )

    transacao = Transacao(
        usuario_id=usuario.id,
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
