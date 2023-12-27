"""Create phone number for user column

Revision ID: 37a513db33d4
Revises: 
Create Date: 2023-11-28 21:54:04.066040

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "37a513db33d4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("phone_number", sa.String(length=13), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "phone_number")
