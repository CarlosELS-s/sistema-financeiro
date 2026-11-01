
import calendar

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

from database import get_db
from models import (
    Usuario,
    Transacao,
    CartaoCredito,
    CompraCartao,
    FaturaCartao,
)
from schemas import TransacaoCreate, TransacaoResponse
from auth import get_usuario_atual

router = APIRouter(
    prefix="/api",
    tags=["Financeiro"]
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


def calcular_periodo(cartao: CartaoCredito, data_compra: date):
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

    if fatura:
        if fatura.status != "paga":
            fatura.vencimento = vencimento

        return fatura

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
    return int(
        db.query(
            func.coalesce(
                func.sum(CompraCartao.valor_centavos), 0
            )
        ).filter(
            CompraCartao.fatura_id == fatura_id
        ).scalar() or 0
    )


def total_utilizado(db: Session, cartao_id: int) -> int:
    faturas = db.query(FaturaCartao).filter(
        FaturaCartao.cartao_id == cartao_id,
        FaturaCartao.status != "paga"
    ).all()

    return sum(
        total_fatura(db, fatura.id)
        for fatura in faturas
    )


def registrar_compra_parcelada(
    db: Session,
    cartao: CartaoCredito,
    descricao: str,
    categoria: str,
    valor_centavos: int,
    data_compra: date,
    quantidade_parcelas: int
):
    if quantidade_parcelas < 1 or quantidade_parcelas > 60:
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

    valor_base = valor_centavos // quantidade_parcelas
    resto = valor_centavos % quantidade_parcelas

    compras = []

    for numero in range(1, quantidade_parcelas + 1):
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
                f"A fatura de {mes:02d}/{ano} já está paga."
            )

        compra = CompraCartao(
            fatura_id=fatura.id,
            descricao=(
                f"{descricao} ({numero}/{quantidade_parcelas})"
                if quantidade_parcelas > 1
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


def subquery_pagamentos_usuario(usuario_id: int, db: Session):
    return db.query(
        FaturaCartao.transacao_id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CartaoCredito.usuario_id == usuario_id,
        FaturaCartao.transacao_id.isnot(None)
    )


def validar_mes(mes: str):
    try:
        ano, numero_mes = map(int, mes.split("-"))

        if not 1 <= numero_mes <= 12:
            raise ValueError()

        return ano, numero_mes

    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Mês inválido. Utilize YYYY-MM."
        )


def periodo_mes(ano: int, numero_mes: int):
    inicio = date(ano, numero_mes, 1)

    if numero_mes == 12:
        fim = date(ano + 1, 1, 1)
    else:
        fim = date(ano, numero_mes + 1, 1)

    return inicio, fim


# =====================================
# CADASTRAR TRANSAÇÃO
# =====================================

@router.post("/transacoes")
def criar_transacao(
    dados: TransacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    try:
        valor_centavos = para_centavos(dados.valor)

        if dados.forma_pagamento == "credito":
            if dados.tipo != "despesa":
                raise HTTPException(
                    400,
                    "Cartão de crédito só pode ser utilizado em despesas."
                )

            if not dados.cartao_id:
                raise HTTPException(
                    400,
                    "Selecione um cartão de crédito."
                )

            cartao = db.query(CartaoCredito).filter(
                CartaoCredito.id == dados.cartao_id,
                CartaoCredito.usuario_id == usuario.id,
                CartaoCredito.ativo == True
            ).first()

            if not cartao:
                raise HTTPException(
                    404,
                    "Cartão não encontrado ou inativo."
                )

            registrar_compra_parcelada(
                db=db,
                cartao=cartao,
                descricao=dados.descricao.strip(),
                categoria=dados.categoria.strip(),
                valor_centavos=valor_centavos,
                data_compra=dados.data,
                quantidade_parcelas=dados.parcelas
            )

            db.commit()

            return {
                "mensagem": "Compra no crédito registrada com sucesso!",
                "forma_pagamento": "credito",
                "parcelas": dados.parcelas,
                "valor_centavos": valor_centavos
            }

        nova_transacao = Transacao(
            usuario_id=usuario.id,
            descricao=dados.descricao.strip(),
            tipo=dados.tipo,
            categoria=dados.categoria.strip(),
            valor_centavos=valor_centavos,
            data=dados.data
        )

        db.add(nova_transacao)
        db.commit()
        db.refresh(nova_transacao)

        return {
            "mensagem": "Movimentação cadastrada com sucesso!",
            "transacao": {
                "id": nova_transacao.id,
                "descricao": nova_transacao.descricao,
                "tipo": nova_transacao.tipo,
                "categoria": nova_transacao.categoria,
                "valor": nova_transacao.valor,
                "data": nova_transacao.data.isoformat()
            }
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# LISTAR TRANSAÇÕES
# =====================================

@router.get(
    "/transacoes",
    response_model=list[TransacaoResponse]
)
def listar_transacoes(
    tipo: str | None = None,
    mes: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    query = db.query(Transacao).filter(
        Transacao.usuario_id == usuario.id
    )

    if tipo:
        if tipo not in ["receita", "despesa"]:
            raise HTTPException(400, "Tipo inválido.")

        query = query.filter(
            Transacao.tipo == tipo
        )

    if mes:
        ano, numero_mes = validar_mes(mes)
        inicio, fim = periodo_mes(ano, numero_mes)

        query = query.filter(
            Transacao.data >= inicio,
            Transacao.data < fim
        )

    return query.order_by(
        Transacao.data.desc(),
        Transacao.id.desc()
    ).all()


# =====================================
# LISTAR MOVIMENTAÇÕES
# =====================================

@router.get("/movimentos")
def listar_movimentos(
    tipo: str | None = None,
    mes: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    if tipo and tipo not in ["receita", "despesa"]:
        raise HTTPException(400, "Tipo inválido.")

    if mes:
        ano, numero_mes = validar_mes(mes)
    else:
        hoje = date.today()
        ano = hoje.year
        numero_mes = hoje.month

    query = db.query(Transacao).filter(
        Transacao.usuario_id == usuario.id
    )

    if tipo:
        query = query.filter(Transacao.tipo == tipo)

    if mes:
        inicio, fim = periodo_mes(ano, numero_mes)

        query = query.filter(
            Transacao.data >= inicio,
            Transacao.data < fim
        )

    pagamentos_faturas = subquery_pagamentos_usuario(
        usuario.id,
        db
    )

    transacoes = query.filter(
        ~Transacao.id.in_(pagamentos_faturas)
    ).all()

    movimentos = []

    for t in transacoes:
        movimentos.append({
            "id": t.id,
            "origem": "transacao",
            "descricao": t.descricao,
            "tipo": t.tipo,
            "categoria": t.categoria,
            "valor": t.valor,
            "data": t.data.isoformat()
        })

    parcelas = db.query(
        CompraCartao,
        FaturaCartao
    ).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CartaoCredito.usuario_id == usuario.id,
        FaturaCartao.ano == ano,
        FaturaCartao.mes == numero_mes
    ).all()

    if tipo is None or tipo == "despesa":
        for compra, fatura in parcelas:
            movimentos.append({
                "id": compra.id,
                "origem": "cartao",
                "descricao": compra.descricao,
                "tipo": "despesa",
                "categoria": compra.categoria or "Outros",
                "valor": compra.valor_centavos / 100,
                "data": compra.data.isoformat(),
                "vencimento": fatura.vencimento.isoformat()
            })

    movimentos.sort(
        key=lambda item: (item["data"], item["id"]),
        reverse=True
    )

    return movimentos


# =====================================
# EDITAR TRANSAÇÃO
# =====================================

@router.put(
    "/transacoes/{transacao_id}",
    response_model=TransacaoResponse
)
def editar_transacao(
    transacao_id: int,
    dados: TransacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    transacao = db.query(Transacao).filter(
        Transacao.id == transacao_id,
        Transacao.usuario_id == usuario.id
    ).first()

    if not transacao:
        raise HTTPException(
            404,
            "Transação não encontrada."
        )

    if dados.forma_pagamento == "credito":
        raise HTTPException(
            400,
            "Para alterar uma compra no crédito, utilize o controle de cartões."
        )

    transacao.descricao = dados.descricao.strip()
    transacao.tipo = dados.tipo
    transacao.categoria = dados.categoria.strip()
    transacao.valor_centavos = para_centavos(dados.valor)
    transacao.data = dados.data

    db.commit()
    db.refresh(transacao)

    return transacao


# =====================================
# EXCLUIR TRANSAÇÃO
# =====================================

@router.delete("/transacoes/{transacao_id}")
def excluir_transacao(
    transacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    transacao = db.query(Transacao).filter(
        Transacao.id == transacao_id,
        Transacao.usuario_id == usuario.id
    ).first()

    if not transacao:
        raise HTTPException(
            404,
            "Transação não encontrada."
        )

    db.delete(transacao)
    db.commit()

    return {
        "message": "Transação excluída com sucesso."
    }


# =====================================
# DASHBOARD
# =====================================

@router.get("/dashboard")
def dashboard(
    mes: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    if mes is None:
        mes = date.today().strftime("%Y-%m")

    ano, numero_mes = validar_mes(mes)
    inicio, fim = periodo_mes(ano, numero_mes)

    pagamentos_faturas = subquery_pagamentos_usuario(
        usuario.id,
        db
    )

    def somar(tipo, data_inicio=None, data_fim=None):
        query = db.query(
            func.coalesce(
                func.sum(Transacao.valor_centavos), 0
            )
        ).filter(
            Transacao.usuario_id == usuario.id,
            Transacao.tipo == tipo,
            ~Transacao.id.in_(pagamentos_faturas)
        )

        if data_inicio:
            query = query.filter(
                Transacao.data >= data_inicio
            )

        if data_fim:
            query = query.filter(
                Transacao.data < data_fim
            )

        return int(query.scalar() or 0)

    receitas_mes = somar("receita", inicio, fim)
    despesas_normais_mes = somar("despesa", inicio, fim)

    receitas_total = somar("receita")
    despesas_normais_total = somar("despesa")

    parcelas_mes = int(
        db.query(
            func.coalesce(
                func.sum(CompraCartao.valor_centavos), 0
            )
        ).join(
            FaturaCartao,
            CompraCartao.fatura_id == FaturaCartao.id
        ).join(
            CartaoCredito,
            FaturaCartao.cartao_id == CartaoCredito.id
        ).filter(
            CartaoCredito.usuario_id == usuario.id,
            FaturaCartao.ano == ano,
            FaturaCartao.mes == numero_mes
        ).scalar() or 0
    )

    parcelas_total = int(
        db.query(
            func.coalesce(
                func.sum(CompraCartao.valor_centavos), 0
            )
        ).join(
            FaturaCartao,
            CompraCartao.fatura_id == FaturaCartao.id
        ).join(
            CartaoCredito,
            FaturaCartao.cartao_id == CartaoCredito.id
        ).filter(
            CartaoCredito.usuario_id == usuario.id
        ).scalar() or 0
    )

    despesas_mes = despesas_normais_mes + parcelas_mes
    despesas_total = despesas_normais_total + parcelas_total

    despesas_categoria = db.query(
        Transacao.categoria,
        func.sum(Transacao.valor_centavos)
    ).filter(
        Transacao.usuario_id == usuario.id,
        Transacao.tipo == "despesa",
        Transacao.data >= inicio,
        Transacao.data < fim,
        ~Transacao.id.in_(pagamentos_faturas)
    ).group_by(
        Transacao.categoria
    ).all()

    categorias = {}

    for categoria, valor in despesas_categoria:
        categorias[categoria or "Outros"] = int(valor or 0)

    categorias_cartao = db.query(
        CompraCartao.categoria,
        func.sum(CompraCartao.valor_centavos)
    ).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CartaoCredito.usuario_id == usuario.id,
        FaturaCartao.ano == ano,
        FaturaCartao.mes == numero_mes
    ).group_by(
        CompraCartao.categoria
    ).all()

    for categoria, valor in categorias_cartao:
        nome_categoria = categoria or "Outros"

        categorias[nome_categoria] = (
            categorias.get(nome_categoria, 0)
            + int(valor or 0)
        )

    ultimas = db.query(Transacao).filter(
        Transacao.usuario_id == usuario.id,
        ~Transacao.id.in_(pagamentos_faturas)
    ).order_by(
        Transacao.data.desc(),
        Transacao.id.desc()
    ).limit(10).all()

    movimentacoes = []

    for t in ultimas:
        movimentacoes.append({
            "id": t.id,
            "origem": "transacao",
            "descricao": t.descricao,
            "tipo": t.tipo,
            "categoria": t.categoria,
            "valor": t.valor,
            "data": t.data.isoformat()
        })

    ultimas_cartao = db.query(
        CompraCartao,
        FaturaCartao
    ).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CartaoCredito.usuario_id == usuario.id
    ).order_by(
        CompraCartao.data.desc(),
        CompraCartao.id.desc()
    ).limit(10).all()

    for compra, fatura in ultimas_cartao:
        movimentacoes.append({
            "id": compra.id,
            "origem": "cartao",
            "descricao": compra.descricao,
            "tipo": "despesa",
            "categoria": compra.categoria or "Outros",
            "valor": compra.valor_centavos / 100,
            "data": compra.data.isoformat(),
            "vencimento": fatura.vencimento.isoformat()
        })

    movimentacoes.sort(
        key=lambda item: (item["data"], item["id"]),
        reverse=True
    )

    movimentacoes = movimentacoes[:5]

    return {
        "mes": mes,
        "saldo_total": (
            receitas_total - despesas_total
        ) / 100,
        "receitas_total": receitas_total / 100,
        "despesas_total": despesas_total / 100,
        "receitas_mes": receitas_mes / 100,
        "despesas_mes": despesas_mes / 100,
        "saldo_mes": (
            receitas_mes - despesas_mes
        ) / 100,
        "despesas_categoria": [
            {
                "categoria": categoria,
                "valor": valor / 100
            }
            for categoria, valor in categorias.items()
        ],
        "ultimas_transacoes": movimentacoes
    }


# =====================================
# EXPORTAR EXCEL
# =====================================

@router.get("/planilhas/exportar")
def exportar_excel(
    mes: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    # Validar mês selecionado
    ano, numero_mes = validar_mes(mes)
    inicio, fim = periodo_mes(ano, numero_mes)

    # Evitar contabilizar o pagamento da fatura
    # novamente como uma despesa.
    pagamentos_faturas = subquery_pagamentos_usuario(
        usuario.id,
        db
    )

    # Buscar transações normais do usuário no mês.
    transacoes = db.query(Transacao).filter(
        Transacao.usuario_id == usuario.id,
        Transacao.data >= inicio,
        Transacao.data < fim,
        ~Transacao.id.in_(pagamentos_faturas)
    ).all()

    # Buscar parcelas das faturas do mês selecionado.
    parcelas = db.query(
        CompraCartao,
        FaturaCartao
    ).join(
        FaturaCartao,
        CompraCartao.fatura_id == FaturaCartao.id
    ).join(
        CartaoCredito,
        FaturaCartao.cartao_id == CartaoCredito.id
    ).filter(
        CartaoCredito.usuario_id == usuario.id,
        FaturaCartao.ano == ano,
        FaturaCartao.mes == numero_mes
    ).all()

    # Criar lista única de movimentações.
    movimentacoes = []

    for t in transacoes:
        movimentacoes.append({
            "descricao": t.descricao,
            "tipo": t.tipo,
            "categoria": t.categoria or "Outros",
            "valor": t.valor_centavos / 100,
            "data": t.data,
            "origem": "Transação"
        })

    for compra, fatura in parcelas:
        movimentacoes.append({
            "descricao": compra.descricao,
            "tipo": "despesa",
            "categoria": compra.categoria or "Outros",
            "valor": compra.valor_centavos / 100,
            "data": compra.data,
            "origem": "Cartão de crédito"
        })

    # Ordenar por data.
    movimentacoes.sort(
        key=lambda item: item["data"]
    )

    # Criar arquivo Excel.
    arquivo = Workbook()
    planilha = arquivo.active
    planilha.title = "Movimentações"

    cabecalho = [
        "Descrição",
        "Tipo",
        "Categoria",
        "Valor",
        "Data",
        "Origem"
    ]

    planilha.append(cabecalho)

    # Estilizar cabeçalho.
    for celula in planilha[1]:
        celula.font = Font(
            bold=True,
            color="FFFFFF"
        )

        celula.fill = PatternFill(
            fill_type="solid",
            fgColor="166534"
        )

        celula.alignment = Alignment(
            horizontal="center"
        )

    # Inserir movimentações.
    for movimento in movimentacoes:
        planilha.append([
            movimento["descricao"],
            movimento["tipo"],
            movimento["categoria"],
            movimento["valor"],
            movimento["data"],
            movimento["origem"]
        ])

    # Formatação.
    planilha.freeze_panes = "A2"
    planilha.auto_filter.ref = planilha.dimensions

    larguras = {
        "A": 35,
        "B": 15,
        "C": 22,
        "D": 18,
        "E": 18,
        "F": 22
    }

    for coluna, largura in larguras.items():
        planilha.column_dimensions[coluna].width = largura

    for linha in range(2, planilha.max_row + 1):
        planilha.cell(
            linha,
            4
        ).number_format = '"R$" #,##0.00'

        planilha.cell(
            linha,
            5
        ).number_format = "DD/MM/YYYY"

    # Preparar download.
    buffer = BytesIO()
    arquivo.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
            f'attachment; filename="movimentacoes_{mes}.xlsx"'
        }
    )

# =====================================
# IMPORTAR EXCEL
# =====================================

@router.post("/planilhas/importar")
async def importar_excel(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    if (
        not arquivo.filename
        or not arquivo.filename.lower().endswith(".xlsx")
    ):
        raise HTTPException(
            400,
            "Envie uma planilha no formato .xlsx."
        )

    conteudo = await arquivo.read(
        10 * 1024 * 1024 + 1
    )

    if len(conteudo) > 10 * 1024 * 1024:
        raise HTTPException(
            400,
            "A planilha deve ter no máximo 10 MB."
        )

    try:
        planilha_excel = load_workbook(
            BytesIO(conteudo),
            read_only=True,
            data_only=True
        )

        planilha = planilha_excel.active

        cabecalhos = [
            str(c.value or "").strip().lower()
            for c in next(planilha.iter_rows(max_row=1))
        ]

        aliases = {
            "descricao": ["descrição", "descricao"],
            "tipo": ["tipo"],
            "categoria": ["categoria"],
            "valor": ["valor"],
            "data": ["data"]
        }

        indices = {}

        for campo, nomes in aliases.items():
            encontrados = [
                i
                for i, nome in enumerate(cabecalhos)
                if nome in nomes
            ]

            if not encontrados:
                raise ValueError(
                    f"A coluna '{campo}' não foi encontrada."
                )

            indices[campo] = encontrados[0]

        novas = []

        for numero_linha, linha in enumerate(
            planilha.iter_rows(min_row=2, values_only=True),
            start=2
        ):
            if not any(valor is not None for valor in linha):
                continue

            try:
                descricao = str(
                    linha[indices["descricao"]] or ""
                ).strip()

                tipo = str(
                    linha[indices["tipo"]] or ""
                ).strip().lower()

                categoria = str(
                    linha[indices["categoria"]] or ""
                ).strip()

                valor_original = linha[indices["valor"]]
                data_original = linha[indices["data"]]

                if not descricao or len(descricao) > 200:
                    raise ValueError("Descrição inválida.")

                if tipo not in ["receita", "despesa"]:
                    raise ValueError(
                        "Tipo deve ser receita ou despesa."
                    )

                if not categoria or len(categoria) > 100:
                    raise ValueError("Categoria inválida.")

                if isinstance(valor_original, str):
                    valor_original = Decimal(
                        valor_original.strip()
                        .replace(".", "")
                        .replace(",", ".")
                    )
                else:
                    valor_original = Decimal(
                        str(valor_original)
                    )

                if (
                    not valor_original.is_finite()
                    or valor_original <= 0
                    or valor_original > Decimal("9999999999.99")
                ):
                    raise ValueError("Valor inválido.")

                valor_centavos = int(
                    (
                        valor_original * 100
                    ).quantize(
                        Decimal("1"),
                        rounding=ROUND_HALF_UP
                    )
                )

                if isinstance(data_original, datetime):
                    data_transacao = data_original.date()

                elif isinstance(data_original, date):
                    data_transacao = data_original

                elif isinstance(data_original, str):
                    try:
                        data_transacao = date.fromisoformat(
                            data_original.strip()
                        )
                    except ValueError:
                        data_transacao = datetime.strptime(
                            data_original.strip(),
                            "%d/%m/%Y"
                        ).date()

                else:
                    raise ValueError("Data inválida.")

                novas.append(
                    Transacao(
                        usuario_id=usuario.id,
                        descricao=descricao,
                        tipo=tipo,
                        categoria=categoria,
                        valor_centavos=valor_centavos,
                        data=data_transacao
                    )
                )

            except (
                ValueError,
                InvalidOperation,
                TypeError
            ) as erro:
                raise ValueError(
                    f"Linha {numero_linha}: {erro}"
                )

        if not novas:
            raise ValueError(
                "A planilha não contém movimentações."
            )

        db.add_all(novas)
        db.commit()

        return {
            "message": "Planilha importada com sucesso!",
            "importadas": len(novas)
        }

    except Exception as erro:
        db.rollback()

        if isinstance(erro, HTTPException):
            raise erro

        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

    finally:
        if "planilha_excel" in locals():
            planilha_excel.close()
