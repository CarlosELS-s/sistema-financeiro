
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, ContaFixa, ContaMensal, Transacao
from schemas import (
    ContaFixaCreate,
    ContaFixaResponse,
    ContaFixaUpdate,
    ContaPagar,
)
from auth import get_usuario_atual


router = APIRouter(
    prefix="/api/contas-fixas",
    tags=["Contas Fixas"]
)


# =====================================
# FUNÇÕES AUXILIARES
# =====================================

def converter_centavos(valor: Decimal) -> int:
    return int(
        (Decimal(str(valor)) * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def primeiro_dia(ano: int, mes: int) -> date:
    return date(ano, mes, 1)


def validar_mes(mes: str):
    try:
        ano, numero_mes = map(int, mes.split("-"))

        if not 1 <= numero_mes <= 12 or ano < 1:
            raise ValueError()

        return ano, numero_mes

    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Mês inválido. Utilize YYYY-MM."
        )


def proximo_mes(ano: int, mes: int):
    if mes == 12:
        return ano + 1, 1

    return ano, mes + 1


def gerar_contas_mensais(
    db: Session,
    conta: ContaFixa,
    ano_alvo: int,
    mes_alvo: int
):
    ano = conta.data_inicio.year
    mes = conta.data_inicio.month

    while (ano, mes) <= (ano_alvo, mes_alvo):

        existente = db.query(ContaMensal).filter(
            ContaMensal.conta_fixa_id == conta.id,
            ContaMensal.ano == ano,
            ContaMensal.mes == mes
        ).first()

        if not existente:
            nova_conta = ContaMensal(
                conta_fixa_id=conta.id,
                ano=ano,
                mes=mes,
                vencimento=primeiro_dia(ano, mes),
                valor_previsto_centavos=conta.valor_centavos,
                status="pendente"
            )

            db.add(nova_conta)

        ano, mes = proximo_mes(ano, mes)

    db.flush()


def buscar_conta_usuario(
    db: Session,
    conta_id: int,
    usuario_id: int
):
    conta = db.query(ContaFixa).filter(
        ContaFixa.id == conta_id,
        ContaFixa.usuario_id == usuario_id
    ).first()

    if not conta:
        raise HTTPException(
            status_code=404,
            detail="Conta fixa não encontrada."
        )

    return conta


# =====================================
# CADASTRAR CONTA FIXA
# =====================================

@router.post("", response_model=ContaFixaResponse)
def criar_conta_fixa(
    dados: ContaFixaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    nova_conta = ContaFixa(
        usuario_id=usuario.id,
        nome=dados.nome.strip(),
        categoria=dados.categoria.strip() or "Conta",
        descricao=dados.descricao.strip() if dados.descricao else None,
        valor_centavos=converter_centavos(dados.valor),
        dia_vencimento=1,
        valor_padrao=True,
        data_inicio=dados.data_inicio,
        ativa=True
    )

    try:
        db.add(nova_conta)
        db.commit()
        db.refresh(nova_conta)

        return nova_conta

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao cadastrar conta fixa."
        )


# =====================================
# LISTAR CONTAS FIXAS
# =====================================

@router.get("", response_model=list[ContaFixaResponse])
def listar_contas_fixas(
    incluir_inativas: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    query = db.query(ContaFixa).filter(
        ContaFixa.usuario_id == usuario.id
    )

    if not incluir_inativas:
        query = query.filter(
            ContaFixa.ativa.is_(True)
        )

    return query.order_by(
        ContaFixa.nome.asc()
    ).all()


# =====================================
# EDITAR CONTA FIXA
# =====================================

@router.put("/{conta_id}", response_model=ContaFixaResponse)
def editar_conta_fixa(
    conta_id: int,
    dados: ContaFixaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    conta = buscar_conta_usuario(
        db,
        conta_id,
        usuario.id
    )

    conta.nome = dados.nome.strip()
    conta.categoria = dados.categoria.strip() or "Conta"
    conta.descricao = dados.descricao.strip() if dados.descricao else None
    conta.valor_centavos = converter_centavos(dados.valor)
    conta.valor_padrao = True
    conta.data_inicio = dados.data_inicio

    try:
        db.commit()
        db.refresh(conta)

        return conta

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao editar conta fixa."
        )


# =====================================
# LISTAR CONTAS MENSAIS
# =====================================

@router.get("/mensais")
def listar_contas_mensais(
    mes: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    if mes is None:
        mes = date.today().strftime("%Y-%m")

    ano, numero_mes = validar_mes(mes)

    ultimo_dia_mes = date(
        ano,
        numero_mes,
        monthrange(ano, numero_mes)[1]
    )

    contas_ativas = db.query(ContaFixa).filter(
        ContaFixa.usuario_id == usuario.id,
        ContaFixa.ativa.is_(True),
        ContaFixa.data_inicio <= ultimo_dia_mes
    ).all()

    for conta in contas_ativas:
        gerar_contas_mensais(
            db,
            conta,
            ano,
            numero_mes
        )

    db.commit()

    registros = db.query(
        ContaMensal,
        ContaFixa
    ).join(
        ContaFixa,
        ContaFixa.id == ContaMensal.conta_fixa_id
    ).filter(
        ContaFixa.usuario_id == usuario.id,
        (
            (
                (ContaMensal.ano == ano)
                & (ContaMensal.mes == numero_mes)
            )
            |
            (
                (ContaMensal.status == "pendente")
                & (
                    (ContaMensal.ano < ano)
                    |
                    (
                        (ContaMensal.ano == ano)
                        & (ContaMensal.mes < numero_mes)
                    )
                )
            )
        )
    ).order_by(
        ContaMensal.ano.asc(),
        ContaMensal.mes.asc(),
        ContaFixa.nome.asc()
    ).all()

    hoje = date.today()
    mes_atual = (hoje.year, hoje.month)

    resultado = []

    for mensal, conta in registros:
        mes_da_conta = (mensal.ano, mensal.mes)

        resultado.append({
            "id": mensal.id,
            "conta_fixa_id": conta.id,
            "nome": conta.nome,
            "categoria": conta.categoria,
            "descricao": conta.descricao,
            "ano": mensal.ano,
            "mes": mensal.mes,
            "vencimento": mensal.vencimento.isoformat(),
            "valor_previsto": mensal.valor_previsto_centavos / 100,
            "valor_pago": (
                mensal.valor_pago_centavos / 100
                if mensal.valor_pago_centavos is not None
                else None
            ),
            "status": mensal.status,
            "data_pagamento": (
                mensal.data_pagamento.isoformat()
                if mensal.data_pagamento
                else None
            ),
            "atrasada": (
                mensal.status == "pendente"
                and mes_da_conta < mes_atual
            ),
            "transacao_id": mensal.transacao_id
        })

    return resultado


# =====================================
# PAGAR CONTA MENSAL
# =====================================

@router.post("/mensais/{conta_mensal_id}/pagar")
def pagar_conta_mensal(
    conta_mensal_id: int,
    dados: ContaPagar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    mensal = db.query(
        ContaMensal
    ).join(
        ContaFixa,
        ContaFixa.id == ContaMensal.conta_fixa_id
    ).filter(
        ContaMensal.id == conta_mensal_id,
        ContaFixa.usuario_id == usuario.id
    ).first()

    if not mensal:
        raise HTTPException(
            status_code=404,
            detail="Conta mensal não encontrada."
        )

    if mensal.status == "paga" or mensal.transacao_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Essa conta já foi paga."
        )

    conta = buscar_conta_usuario(
        db,
        mensal.conta_fixa_id,
        usuario.id
    )

    valor_centavos = converter_centavos(dados.valor_pago)

    try:
        nova_transacao = Transacao(
            usuario_id=usuario.id,
            descricao=f"{conta.nome} (conta fixa)",
            tipo="despesa",
            categoria=conta.categoria,
            valor_centavos=valor_centavos,
            data=dados.data_pagamento
        )

        db.add(nova_transacao)
        db.flush()

        mensal.valor_pago_centavos = valor_centavos
        mensal.data_pagamento = dados.data_pagamento
        mensal.status = "paga"
        mensal.transacao_id = nova_transacao.id

        db.commit()

        return {
            "message": "Conta paga e despesa registrada com sucesso.",
            "conta_mensal_id": mensal.id,
            "transacao_id": nova_transacao.id,
            "valor_pago": valor_centavos / 100,
            "data_pagamento": dados.data_pagamento.isoformat()
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao registrar pagamento da conta."
        )


# =====================================
# ATUALIZAR CONTA FIXA
# =====================================

@router.patch("/{conta_id}")
def atualizar_conta_fixa(
    conta_id: int,
    dados: ContaFixaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    conta = buscar_conta_usuario(
        db,
        conta_id,
        usuario.id
    )

    if dados.nome is not None:
        conta.nome = dados.nome.strip()

    if dados.categoria is not None:
        conta.categoria = dados.categoria.strip() or "Conta"

    if dados.descricao is not None:
        conta.descricao = dados.descricao.strip() or None

    if dados.valor is not None:
        novo_valor_centavos = converter_centavos(
            dados.valor
        )

        conta.valor_centavos = novo_valor_centavos

        db.query(ContaMensal).filter(
            ContaMensal.conta_fixa_id == conta_id,
            ContaMensal.status == "pendente"
        ).update(
            {
                ContaMensal.valor_previsto_centavos:
                    novo_valor_centavos
            },
            synchronize_session=False
        )

    try:
        db.commit()
        db.refresh(conta)

        return {
            "message": "Conta atualizada com sucesso.",
            "valor_atualizado": conta.valor_centavos / 100
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao atualizar a conta fixa."
        )


# =====================================
# EXCLUIR CONTA FIXA DEFINITIVAMENTE
# =====================================

@router.delete("/{conta_id}")
def excluir_conta_fixa(
    conta_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    conta = buscar_conta_usuario(
        db,
        conta_id,
        usuario.id
    )

    try:
        mensais = db.query(ContaMensal).filter(
            ContaMensal.conta_fixa_id == conta.id
        ).all()

        # Impede apagar transações que já foram geradas
        # por pagamentos de contas fixas.
        if any(m.transacao_id is not None for m in mensais):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Esta conta possui pagamentos registrados. "
                    "Não é possível excluí-la definitivamente."
                )
            )

        db.query(ContaMensal).filter(
            ContaMensal.conta_fixa_id == conta.id
        ).delete(
            synchronize_session=False
        )

        db.delete(conta)
        db.commit()

        return {
            "message": "Conta removida definitivamente."
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao excluir a conta fixa."
        )
