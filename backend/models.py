from datetime import date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from database import Base


# =====================================
# USUÁRIOS
# =====================================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)

    ativo = Column(Boolean, default=True, nullable=False)

    # Recuperação de senha
    codigo_recuperacao_hash = Column(String(255), nullable=True)
    codigo_recuperacao_expira = Column(DateTime(timezone=True), nullable=True)
    codigo_recuperacao_tentativas = Column(Integer, default=0, nullable=False)

    # Controle de solicitações
    codigo_recuperacao_solicitado_em = Column(
        DateTime(timezone=True),
        nullable=True
    )

    codigo_recuperacao_solicitacoes = Column(
        Integer,
        default=0,
        nullable=False
    )

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =====================================
# TRANSAÇÕES
# =====================================

class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    descricao = Column(String(200), nullable=False)
    tipo = Column(String(20), nullable=False)
    categoria = Column(String(100), nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    data = Column(Date, nullable=False)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    @property
    def valor(self):
        return self.valor_centavos / 100


# =====================================
# CONTAS FIXAS
# =====================================

class ContaFixa(Base):
    __tablename__ = "contas_fixas"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    nome = Column(String(150), nullable=False)
    categoria = Column(String(100), nullable=False)
    descricao = Column(String(300), nullable=True)
    valor_centavos = Column(Integer, nullable=False)
    dia_vencimento = Column(Integer, nullable=False)
    valor_padrao = Column(Boolean, default=True, nullable=False)
    data_inicio = Column(Date, default=date.today, nullable=False)
    ativa = Column(Boolean, default=True, nullable=False)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =====================================
# CONTROLE MENSAL DAS CONTAS
# =====================================

class ContaMensal(Base):
    __tablename__ = "contas_mensais"

    __table_args__ = (
        UniqueConstraint(
            "conta_fixa_id",
            "ano",
            "mes",
            name="uq_conta_fixa_mes"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    conta_fixa_id = Column(
        Integer,
        ForeignKey("contas_fixas.id"),
        nullable=False
    )

    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    vencimento = Column(Date, nullable=False)
    valor_previsto_centavos = Column(Integer, nullable=False)
    valor_pago_centavos = Column(Integer, nullable=True)

    status = Column(
        String(20),
        default="pendente",
        nullable=False
    )

    data_pagamento = Column(Date, nullable=True)

    transacao_id = Column(
        Integer,
        ForeignKey("transacoes.id"),
        nullable=True,
        unique=True
    )

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =====================================
# CARTÕES DE CRÉDITO
# =====================================

class CartaoCredito(Base):
    __tablename__ = "cartoes_credito"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    nome = Column(String(100), nullable=False)
    banco = Column(String(100), nullable=True)
    limite_centavos = Column(Integer, nullable=False)
    dia_fechamento = Column(Integer, nullable=False)
    dia_vencimento = Column(Integer, nullable=False)

    ativo = Column(Boolean, default=True, nullable=False)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =====================================
# FATURAS DO CARTÃO
# =====================================

class FaturaCartao(Base):
    __tablename__ = "faturas_cartao"

    __table_args__ = (
        UniqueConstraint(
            "cartao_id",
            "ano",
            "mes",
            name="uq_fatura_cartao_mes"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    cartao_id = Column(
        Integer,
        ForeignKey("cartoes_credito.id"),
        nullable=False
    )

    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    vencimento = Column(Date, nullable=False)

    status = Column(
        String(20),
        default="aberta",
        nullable=False
    )

    transacao_id = Column(
        Integer,
        ForeignKey("transacoes.id"),
        nullable=True,
        unique=True
    )

    data_pagamento = Column(Date, nullable=True)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =====================================
# COMPRAS NO CARTÃO
# =====================================

class CompraCartao(Base):
    __tablename__ = "compras_cartao"

    id = Column(Integer, primary_key=True, index=True)

    fatura_id = Column(
        Integer,
        ForeignKey("faturas_cartao.id"),
        nullable=False
    )

    descricao = Column(String(200), nullable=False)
    categoria = Column(String(100), nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    data = Column(Date, nullable=False)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =====================================
# ORÇAMENTOS MENSAIS POR CATEGORIA
# =====================================

class Orcamento(Base):
    __tablename__ = "orcamentos"

    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "ano",
            "mes",
            "categoria",
            name="uq_orcamento_usuario_mes_categoria"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    categoria = Column(String(100), nullable=False)

    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)

    valor_limite_centavos = Column(Integer, nullable=False)
    cartoes_ids = Column(String(1000), nullable=True)
    fixado = Column(Boolean, default=False, nullable=False)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
