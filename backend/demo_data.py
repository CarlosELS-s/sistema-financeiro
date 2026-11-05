
from datetime import date


def dados_dashboard(mes: str):
    ano, numero_mes = map(int, mes.split("-"))

    return {
        "mes": mes,
        "saldo_total": 7350.00,
        "receitas_total": 8500.00,
        "despesas_total": 1150.00,
        "receitas_mes": 8500.00,
        "despesas_mes": 1150.00,
        "saldo_mes": 7350.00,
        "despesas_categoria": [
            {"categoria": "Moradia", "valor": 650.00},
            {"categoria": "Alimentação", "valor": 300.00},
            {"categoria": "Transporte", "valor": 200.00}
        ],
        "ultimas_transacoes": [
            {
                "id": 9001,
                "origem": "transacao",
                "descricao": "Salário demonstrativo",
                "tipo": "receita",
                "categoria": "Salário",
                "valor": 8500.00,
                "data": date(ano, numero_mes, 5).isoformat()
            },
            {
                "id": 9002,
                "origem": "transacao",
                "descricao": "Conta de energia",
                "tipo": "despesa",
                "categoria": "Moradia",
                "valor": 250.00,
                "data": date(ano, numero_mes, 8).isoformat()
            },
            {
                "id": 9003,
                "origem": "transacao",
                "descricao": "Compras de supermercado",
                "tipo": "despesa",
                "categoria": "Alimentação",
                "valor": 300.00,
                "data": date(ano, numero_mes, 10).isoformat()
            }
        ]
    }


def dados_transacoes(mes: str | None = None, tipo: str | None = None):
    hoje = date.today()

    transacoes = [
        {
            "id": 9001,
            "descricao": "Salário demonstrativo",
            "tipo": "receita",
            "categoria": "Salário",
            "valor": 8500.00,
            "data": date(hoje.year, hoje.month, 5)
        },
        {
            "id": 9002,
            "descricao": "Conta de energia",
            "tipo": "despesa",
            "categoria": "Moradia",
            "valor": 250.00,
            "data": date(hoje.year, hoje.month, 8)
        },
        {
            "id": 9003,
            "descricao": "Compras de supermercado",
            "tipo": "despesa",
            "categoria": "Alimentação",
            "valor": 300.00,
            "data": date(hoje.year, hoje.month, 10)
        },
        {
            "id": 9004,
            "descricao": "Transporte",
            "tipo": "despesa",
            "categoria": "Transporte",
            "valor": 200.00,
            "data": date(hoje.year, hoje.month, 12)
        }
    ]

    if tipo:
        transacoes = [
            t for t in transacoes
            if t["tipo"] == tipo
        ]

    if mes:
        ano, numero_mes = map(int, mes.split("-"))
        transacoes = [
            t for t in transacoes
            if t["data"].year == ano
            and t["data"].month == numero_mes
        ]

    return [
        {
            **t,
            "data": t["data"].isoformat()
        }
        for t in sorted(
            transacoes,
            key=lambda item: (item["data"], item["id"]),
            reverse=True
        )
    ]


def dados_movimentos(mes: str | None = None, tipo: str | None = None):
    transacoes = dados_transacoes(mes, tipo)

    return [
        {
            **t,
            "origem": "transacao"
        }
        for t in transacoes
    ]


def dados_orcamentos(mes: str):
    ano, numero_mes = map(int, mes.split("-"))

    return {
        "mes": mes,
        "orcamentos": [
            {
                "id": 9101,
                "categoria": "Alimentação",
                "ano": ano,
                "mes": numero_mes,
                "limite": 800.00,
                "gasto": 300.00,
                "restante": 500.00,
                "percentual": 37.5,
                "ultrapassou": False,
                "cartoes_ids": None,
                "fixado": True
            },
            {
                "id": 9102,
                "categoria": "Moradia",
                "ano": ano,
                "mes": numero_mes,
                "limite": 1000.00,
                "gasto": 250.00,
                "restante": 750.00,
                "percentual": 25.0,
                "ultrapassou": False,
                "cartoes_ids": None,
                "fixado": True
            },
            {
                "id": 9103,
                "categoria": "Transporte",
                "ano": ano,
                "mes": numero_mes,
                "limite": 400.00,
                "gasto": 200.00,
                "restante": 200.00,
                "percentual": 50.0,
                "ultrapassou": False,
                "cartoes_ids": None,
                "fixado": False
            }
        ]
    }
