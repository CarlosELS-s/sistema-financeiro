"""controle solicitacoes recuperacao

Revision ID: edd8e8bdc3a8
Revises: 1aca694b8659
Create Date: 2026-11-02 11:42:09.396693
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'edd8e8bdc3a8'
down_revision: Union[str, Sequence[str], None] = '1aca694b8659'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'usuarios',
        sa.Column(
            'codigo_recuperacao_solicitado_em',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    op.add_column(
        'usuarios',
        sa.Column(
            'codigo_recuperacao_solicitacoes',
            sa.Integer(),
            nullable=False,
            server_default='0'
        )
    )


def downgrade() -> None:
    op.drop_column(
        'usuarios',
        'codigo_recuperacao_solicitacoes'
    )

    op.drop_column(
        'usuarios',
        'codigo_recuperacao_solicitado_em'
    )