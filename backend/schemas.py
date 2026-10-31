from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class TransacaoCreate(BaseModel):
    descricao: str = Field(min_length=2, max_length=200)

    tipo: Literal["receita", "despesa"]

    categoria: str = Field(min_length=2, max_length=100)

    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    data: date


class TransacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    tipo: str
    categoria: str
    valor: float
    data: date