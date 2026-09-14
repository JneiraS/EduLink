"""Add calendar_events table

Revision ID: 9c14f2e6a7bd
Revises: 78466f6d8b58
Create Date: 2026-09-13 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c14f2e6a7bd'
down_revision: Union[str, None] = '78466f6d8b58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('calendar_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('class_name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('priority', sa.String(length=20), nullable=False),
    sa.Column('start_date', sa.DateTime(), nullable=False),
    sa.Column('end_date', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_events_start_date'), 'calendar_events', ['start_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_calendar_events_start_date'), table_name='calendar_events')
    op.drop_table('calendar_events')