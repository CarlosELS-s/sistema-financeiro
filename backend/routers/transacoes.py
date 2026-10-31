from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

from fastapi.responses import StreamingResponse

from database import get_db
from models import Transacao
from schemas import TransacaoCreate, TransacaoResponse


router = APIRouter(
    prefix="/api",
    tags=["Financeiro"]
)


# =====================================
# CADASTRAR TRANSAÇÃO
# =====================================

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


# =====================================
# LISTAR TRANSAÇÕES
# =====================================

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
                detail="Tipo inválido."
            )

        query = query.filter(Transacao.tipo == tipo)

    if mes:
        try:
            ano, numero_mes = map(int, mes.split("-"))

            if not 1 <= numero_mes <= 12:
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


# =====================================
# EDITAR TRANSAÇÃO
# =====================================

@router.put("/transacoes/{transacao_id}", response_model=TransacaoResponse)
def editar_transacao(
    transacao_id: int,
    dados: TransacaoCreate,
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

    transacao.descricao = dados.descricao.strip()
    transacao.tipo = dados.tipo
    transacao.categoria = dados.categoria.strip()
    transacao.valor_centavos = int(dados.valor * 100)
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


# =====================================
# DASHBOARD
# =====================================

@router.get("/dashboard")
def dashboard(
    mes: str | None = None,
    db: Session = Depends(get_db)
):
    if mes is None:
        mes = date.today().strftime("%Y-%m")

    try:
        ano, numero_mes = map(int, mes.split("-"))

        if not 1 <= numero_mes <= 12:
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
        "saldo_total": (receitas_total - despesas_total) / 100,
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


# =====================================
# EXPORTAR EXCEL
# =====================================

@router.get("/planilhas/exportar")
def exportar_excel(db: Session = Depends(get_db)):

    transacoes = db.query(Transacao).order_by(
        Transacao.data.asc(),
        Transacao.id.asc()
    ).all()

    arquivo = Workbook()

    planilha = arquivo.active
    planilha.title = "Movimentações"

    cabecalho = [
        "Descrição",
        "Tipo",
        "Categoria",
        "Valor",
        "Data"
    ]

    planilha.append(cabecalho)

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

    for t in transacoes:
        planilha.append([
            t.descricao,
            t.tipo,
            t.categoria,
            t.valor_centavos / 100,
            t.data
        ])

    planilha.freeze_panes = "A2"
    planilha.auto_filter.ref = planilha.dimensions

    planilha.column_dimensions["A"].width = 30
    planilha.column_dimensions["B"].width = 15
    planilha.column_dimensions["C"].width = 22
    planilha.column_dimensions["D"].width = 18
    planilha.column_dimensions["E"].width = 18

    for linha in range(2, planilha.max_row + 1):
        planilha.cell(linha, 4).number_format = '"R$" #,##0.00'
        planilha.cell(linha, 5).number_format = "DD/MM/YYYY"

    buffer = BytesIO()
    arquivo.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            'attachment; filename="movimentacoes_financeiras.xlsx"'
        }
    )


# =====================================
# IMPORTAR EXCEL
# =====================================

@router.post("/planilhas/importar")
async def importar_excel(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    if not arquivo.filename or not arquivo.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Envie uma planilha no formato .xlsx."
        )

    conteudo = await arquivo.read(10 * 1024 * 1024 + 1)

    if len(conteudo) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="A planilha deve ter no máximo 10 MB."
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
                i for i, nome in enumerate(cabecalhos)
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
                    raise ValueError("Tipo deve ser receita ou despesa.")

                if not categoria or len(categoria) > 100:
                    raise ValueError("Categoria inválida.")

                if isinstance(valor_original, str):
                    valor_original = Decimal(
                        valor_original.strip().replace(".", "").replace(",", ".")
                    )
                else:
                    valor_original = Decimal(str(valor_original))

                if (
                    not valor_original.is_finite()
                    or valor_original <= 0
                    or valor_original > Decimal("9999999999.99")
                ):
                    raise ValueError("Valor inválido.")

                valor_centavos = int(
                    (valor_original * 100).quantize(Decimal("1"))
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
                        descricao=descricao,
                        tipo=tipo,
                        categoria=categoria,
                        valor_centavos=valor_centavos,
                        data=data_transacao
                    )
                )

            except (ValueError, InvalidOperation, TypeError) as erro:
                raise ValueError(
                    f"Linha {numero_linha}: {erro}"
                )

        if not novas:
            raise ValueError("A planilha não contém movimentações.")

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