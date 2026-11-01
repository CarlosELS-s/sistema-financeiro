
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


# =====================================
# USUÁRIOS E AUTENTICAÇÃO
# =====================================

class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    senha: str = Field(min_length=8, max_length=128)


class UsuarioLogin(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    senha: str = Field(min_length=1, max_length=128)


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    ativo: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


# =====================================
# TRANSAÇÕES
# =====================================

class TransacaoCreate(BaseModel):
    descricao: str = Field(min_length=2, max_length=200)
    tipo: Literal["receita", "despesa"]
    categoria: str = Field(min_length=2, max_length=100)

    valor: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    data: date

    forma_pagamento: Literal["pix", "debito", "credito"] | None = None
    cartao_id: int | None = Field(default=None, gt=0)
    parcelas: int = Field(default=1, ge=1, le=60)


class TransacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    tipo: str
    categoria: str
    valor: float
    data: date


# =====================================
# CONTAS FIXAS
# =====================================

class ContaFixaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    categoria: str = Field(default="Conta", min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=300)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    valor_padrao: bool = True
    data_inicio: date = Field(default_factory=date.today)


class ContaFixaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    descricao: str | None
    valor_centavos: int
    dia_vencimento: int
    valor_padrao: bool
    data_inicio: date
    ativa: bool


class ContaMensalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conta_fixa_id: int
    ano: int
    mes: int
    vencimento: date
    valor_previsto_centavos: int
    valor_pago_centavos: int | None
    status: str
    data_pagamento: date | None
    transacao_id: int | None


class ContaFixaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    categoria: str | None = Field(default=None, min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=300)

    valor: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )


class ContaPagar(BaseModel):
    valor_pago: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    data_pagamento: date


# =====================================
# CARTÕES DE CRÉDITO
# =====================================

class CartaoCreditoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    banco: str | None = Field(default=None, max_length=100)

    limite: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    dia_fechamento: int = Field(ge=1, le=31)
    dia_vencimento: int = Field(ge=1, le=31)


class CartaoCreditoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    banco: str | None = Field(default=None, max_length=100)

    limite: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    dia_fechamento: int | None = Field(default=None, ge=1, le=31)
    dia_vencimento: int | None = Field(default=None, ge=1, le=31)


class CartaoCreditoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    banco: str | None
    limite_centavos: int
    dia_fechamento: int
    dia_vencimento: int
    ativo: bool


# =====================================
# COMPRAS NO CARTÃO
# =====================================

class CompraCartaoCreate(BaseModel):
    descricao: str = Field(min_length=2, max_length=200)
    categoria: str = Field(min_length=2, max_length=100)

    valor: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    data: date
    parcelas: int = Field(default=1, ge=1, le=60)


class CompraCartaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fatura_id: int
    descricao: str
    categoria: str
    valor_centavos: int
    data: date


# =====================================
# FATURAS
# =====================================

class FaturaCartaoResponse(BaseModel):
    id: int
    cartao_id: int
    ano: int
    mes: int
    vencimento: date
    status: str
    total_centavos: int
    transacao_id: int | None
    data_pagamento: date | None
    compras: list[CompraCartaoResponse] = Field(default_factory=list)


# =====================================
# PAGAMENTO INTEGRAL DA FATURA
# =====================================

class FaturaCartaoPagar(BaseModel):
    data_pagamento: date
