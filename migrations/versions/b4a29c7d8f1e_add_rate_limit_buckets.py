"""add rate limit buckets

Revision ID: b4a29c7d8f1e
Revises: 522b994cfea0
Create Date: 2026-06-03 15:08:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b4a29c7d8f1e"
down_revision = "522b994cfea0"
branch_labels = None
depends_on = None


def upgrade():
    if not _table_exists("rate_limit_buckets"):
        op.create_table(
            "rate_limit_buckets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scope", sa.Text(), nullable=False),
            sa.Column("identifier", sa.Text(), nullable=False),
            sa.Column("created_at_epoch", sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "idx_rate_limit_scope_identifier_created",
        "rate_limit_buckets",
        ["scope", "identifier", "created_at_epoch"],
    )


def downgrade():
    _drop_index_if_exists(
        "idx_rate_limit_scope_identifier_created",
        "rate_limit_buckets",
    )
    _drop_table_if_exists("rate_limit_buckets")


def _table_exists(table_name):
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_exists(table_name, index_name):
    if not _table_exists(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def _create_index_if_missing(index_name, table_name, columns):
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(index_name, table_name):
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_table_if_exists(table_name):
    if _table_exists(table_name):
        op.drop_table(table_name)
