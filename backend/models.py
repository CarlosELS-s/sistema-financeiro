from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func

from database import Base


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)

    descricao = Column(String(200), nullable=False)

    tipo = Column(String(20), nullable=False)

    categoria = Column(String(100), nullable=False)

    # O valor é armazenado em centavos para evitar
    # problemas de precisão com números decimais.
    valor_centavos = Column(Integer, nullable=False)
    data = Column(Date, nullable=False)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    @property
    def valor(self):
        return self.valor_centavos / 100
