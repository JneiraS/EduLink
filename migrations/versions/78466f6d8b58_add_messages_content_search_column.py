"""add_messages_content_search_column

Revision ID: 78466f6d8b58
Revises: d0626a07e831
Create Date: 2026-08-22 12:10:02.893063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78466f6d8b58'
down_revision: Union[str, None] = 'd0626a07e831'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add content_search column for plaintext search alongside encrypted content.
    op.add_column(
        "messages",
        sa.Column("content_search", sa.Text(), nullable=False, server_default=""),
    )
    # Backfill existing messages: copy content (plaintext) lowercased/trimmed.
    conn = op.get_bind()
    messages = conn.execute(sa.text("SELECT id, content FROM messages")).fetchall()
    for msg_id, content in messages:
        plaintext = content.strip().lower() if content else ""
        conn.execute(
            sa.text("UPDATE messages SET content_search = :ps WHERE id = :id"),
            {"ps": plaintext, "id": msg_id},
        )


def downgrade() -> None:
    op.drop_column("messages", "content_search")
