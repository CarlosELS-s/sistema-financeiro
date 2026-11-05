import uuid
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
from auth import (
    get_usuario_atual,
    get_contexto_atual,
    ContextoVisitante,
)


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

    utilizado = total_utilizado(db, cartao.id)

    if utilizado + valor_centavos > cartao.limite_centavos:
        raise HTTPException(
            400,
            "Esta compra ultrapassa o limite disponível do cartão."
        )

    ano, mes, _ = calcular_periodo(cartao, data_compra)

    valor_base = valor_centavos // parcelas
    resto = valor_centavos % parcelas

    # Gera um identificador único para a compra inteira.
    grupo_compra = str(uuid.uuid4())

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
            grupo_compra=grupo_compra,
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
    contexto=Depends(get_contexto_atual)
):
    # MODO VISITANTE: dados fictícios, sem consultar o banco.
    if isinstance(contexto, ContextoVisitante):
        return [
            {
                "id": 9501,
                "nome": "Cartão principal",
                "banco": "Banco Demonstração",
                "limite_centavos": 500000,
                "utilizado_centavos": 127500,
                "disponivel_centavos": 372500,
                "dia_fechamento": 20,
                "dia_vencimento": 5
            },
            {
                "id": 9502,
                "nome": "Cartão secundário",
                "banco": "Banco Demonstração",
                "limite_centavos": 300000,
                "utilizado_centavos": 45000,
                "disponivel_centavos": 255000,
                "dia_fechamento": 15,
                "dia_vencimento": 10
            }
        ]

    usuario = contexto

    cartoes = db.query(CartaoCredito).filter(
        CartaoCredito.usuario_id == usuario.id,
        CartaoCredito.ativo == True
    ).order_by(
        CartaoCredito.id.desc()
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
            ),
            "grupo_compra": compras[0].grupo_compra
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# LISTAR FATURAS
# =====================================
# =====================================
# LISTAR FATURAS
# =====================================

@router.get("/{cartao_id}/faturas")
def listar_faturas(
    cartao_id: int,
    db: Session = Depends(get_db),
    contexto=Depends(get_contexto_atual)
):
    # MODO VISITANTE: faturas e compras fictícias.
    if isinstance(contexto, ContextoVisitante):
        if cartao_id not in [9501, 9502]:
            raise HTTPException(
                status_code=404,
                detail="Cartão não encontrado."
            )

        hoje = date.today()
        ano = hoje.year
        mes = hoje.month

        if cartao_id == 9501:
            faturas = [
                {
                    "id": 9601,
                    "cartao_id": 9501,
                    "ano": ano,
                    "mes": mes,
                    "vencimento": data_segura(
                        ano + (1 if mes == 12 else 0),
                        1 if mes == 12 else mes + 1,
                        5
                    ).isoformat(),
                    "status": "aberta",
                    "total_centavos": 127500,
                    "transacao_id": None,
                    "data_pagamento": None,
                    "compras": [
                        {
                            "id": 9701,
                            "fatura_id": 9601,
                            "descricao": "Supermercado (1/1)",
                            "categoria": "Alimentação",
                            "valor_centavos": 85000,
                            "data": hoje.isoformat(),
                            "grupo_compra": "demo-compra-1"
                        },
                        {
                            "id": 9702,
                            "fatura_id": 9601,
                            "descricao": "Assinatura (1/1)",
                            "categoria": "Serviços",
                            "valor_centavos": 42500,
                            "data": hoje.isoformat(),
                            "grupo_compra": "demo-compra-2"
                        }
                    ]
                }
            ]

            compras_agrupadas = [
                {
                    "grupo_compra": "demo-compra-1",
                    "identificador": "demo-compra-1",
                    "descricao": "Supermercado",
                    "categoria": "Alimentação",
                    "valor_parcela_centavos": 85000,
                    "valor_total_centavos": 85000,
                    "quantidade_parcelas": 1,
                    "parcelas_registradas": 1,
                    "parcelas": [
                        {
                            "id": 9701,
                            "fatura_id": 9601,
                            "valor_centavos": 85000,
                            "data": hoje.isoformat()
                        }
                    ]
                },
                {
                    "grupo_compra": "demo-compra-2",
                    "identificador": "demo-compra-2",
                    "descricao": "Assinatura",
                    "categoria": "Serviços",
                    "valor_parcela_centavos": 42500,
                    "valor_total_centavos": 42500,
                    "quantidade_parcelas": 1,
                    "parcelas_registradas": 1,
                    "parcelas": [
                        {
                            "id": 9702,
                            "fatura_id": 9601,
                            "valor_centavos": 42500,
                            "data": hoje.isoformat()
                        }
                    ]
                }
            ]

        else:
            faturas = [
                {
                    "id": 9602,
                    "cartao_id": 9502,
                    "ano": ano,
                    "mes": mes,
                    "vencimento": data_segura(
                        ano + (1 if mes == 12 else 0),
                        1 if mes == 12 else mes + 1,
                        10
                    ).isoformat(),
                    "status": "aberta",
                    "total_centavos": 45000,
                    "transacao_id": None,
                    "data_pagamento": None,
                    "compras": [
                        {
                            "id": 9703,
                            "fatura_id": 9602,
                            "descricao": "Compra de exemplo (1/1)",
                            "categoria": "Outros",
                            "valor_centavos": 45000,
                            "data": hoje.isoformat(),
                            "grupo_compra": "demo-compra-3"
                        }
                    ]
                }
            ]

            compras_agrupadas = [
                {
                    "grupo_compra": "demo-compra-3",
                    "identificador": "demo-compra-3",
                    "descricao": "Compra de exemplo",
                    "categoria": "Outros",
                    "valor_parcela_centavos": 45000,
                    "valor_total_centavos": 45000,
                    "quantidade_parcelas": 1,
                    "parcelas_registradas": 1,
                    "parcelas": [
                        {
                            "id": 9703,
                            "fatura_id": 9602,
                            "valor_centavos": 45000,
                            "data": hoje.isoformat()
                        }
                    ]
                }
            ]

        return {
            "faturas": faturas,
            "compras_agrupadas": compras_agrupadas
        }

    # MODO USUÁRIO: dados reais do banco.
    usuario = contexto

    cartao = buscar_cartao_usuario(
        db,
        cartao_id,
        usuario.id
    )

    if not cartao:
        raise HTTPException(404, "Cartão não encontrado.")

    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao.id
    ).order_by(
        FaturaCartao.ano.desc(),
        FaturaCartao.mes.desc()
    ).all()

    todas_compras = db.query(CompraCartao).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).filter(
        FaturaCartao.cartao_id == cartao.id
    ).all()

    grupos = {}

    for compra in todas_compras:
        chave = (
            compra.grupo_compra
            if compra.grupo_compra
            else f"compra-antiga-{compra.id}"
        )

        if chave not in grupos:
            grupos[chave] = {
                "grupo_compra": compra.grupo_compra,
                "descricao": compra.descricao,
                "categoria": compra.categoria,
                "valor_total_centavos": 0,
                "valor_parcela_centavos": compra.valor_centavos,
                "quantidade_parcelas": 0,
                "parcelas": []
            }

        grupo = grupos[chave]
        grupo["valor_total_centavos"] += compra.valor_centavos
        grupo["quantidade_parcelas"] += 1

        grupo["parcelas"].append({
            "id": compra.id,
            "fatura_id": compra.fatura_id,
            "valor_centavos": compra.valor_centavos,
            "data": compra.data
        })

    compras_agrupadas = []

    for chave, grupo in grupos.items():
        descricao = grupo["descricao"] or "Compra"

        import re

        resultado_regex = re.search(
            r"\s*\((\d+)/(\d+)\)$",
            descricao
        )

        if resultado_regex:
            descricao = descricao[:resultado_regex.start()].strip()
            quantidade_total = int(resultado_regex.group(2))
        else:
            quantidade_total = grupo["quantidade_parcelas"]

        compras_agrupadas.append({
            "grupo_compra": grupo["grupo_compra"],
            "identificador": chave,
            "descricao": descricao,
            "categoria": grupo["categoria"],
            "valor_parcela_centavos": grupo["valor_parcela_centavos"],
            "valor_total_centavos": grupo["valor_total_centavos"],
            "quantidade_parcelas": quantidade_total,
            "parcelas_registradas": grupo["quantidade_parcelas"],
            "parcelas": grupo["parcelas"]
        })

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
                    "data": compra.data,
                    "grupo_compra": compra.grupo_compra
                }
                for compra in compras
            ]
        })

    return {
        "faturas": resultado,
        "compras_agrupadas": compras_agrupadas
    }
# =====================================
# EXCLUIR COMPRA E TODAS AS PARCELAS
# =====================================

@router.delete("/compras/grupo/{grupo_compra}")
def excluir_compra_grupo(
    grupo_compra: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    compras = db.query(CompraCartao).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CompraCartao.grupo_compra == grupo_compra,
        CartaoCredito.usuario_id == usuario.id
    ).all()

    if not compras:
        raise HTTPException(
            404,
            "Compra não encontrada."
        )

    faturas_pagas = db.query(FaturaCartao.id).filter(
    FaturaCartao.id.in_(
        [compra.fatura_id for compra in compras]
    ),
    FaturaCartao.status == "paga"
    ).first()

    if faturas_pagas:
            raise HTTPException(
                400,
                "Não é possível excluir uma compra que possui parcelas em faturas pagas."
            )

    try:
        for compra in compras:
            db.delete(compra)

        db.commit()

        return {
            "mensagem": "Compra e todas as parcelas excluídas com sucesso.",
            "parcelas_excluidas": len(compras)
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# EXCLUIR UMA PARCELA INDIVIDUAL
# =====================================

@router.delete("/compras/{compra_id}")
def excluir_parcela(
    compra_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    compra = db.query(CompraCartao).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CompraCartao.id == compra_id,
        CartaoCredito.usuario_id == usuario.id
    ).first()

    if not compra:
        raise HTTPException(
            404,
            "Parcela não encontrada."
        )

    fatura = db.query(FaturaCartao).filter(
        FaturaCartao.id == compra.fatura_id
    ).first()

    if not fatura:
        raise HTTPException(
            404,
            "Fatura não encontrada."
        )

    if fatura.status == "paga":
        raise HTTPException(
            400,
            "Não é possível excluir uma parcela de uma fatura paga."
        )

    try:
        db.delete(compra)
        db.commit()

        return {
            "mensagem": "Parcela excluída com sucesso."
        }

    except Exception:
        db.rollback()
        raise


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