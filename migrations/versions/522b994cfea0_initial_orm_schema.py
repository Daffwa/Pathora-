"""initial orm schema

Revision ID: 522b994cfea0
Revises: 
Create Date: 2026-06-03 02:07:36.170408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '522b994cfea0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("role", sa.Text(), server_default=sa.text("'jobseeker'"), nullable=False),
            sa.Column(
                "account_status",
                sa.Text(),
                server_default=sa.text("'approved'"),
                nullable=False,
            ),
            sa.Column("skills", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("company_name", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("company_position", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("nickname", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("phone", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("birth_date", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("gender", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("domicile", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("bio", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("university", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("faculty", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("major", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("degree", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("semester", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("gpa", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("entry_year", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("desired_positions", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("preferred_program", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("preferred_locations", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("work_arrangement", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("interests", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("linkedin", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("github", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("portfolio_url", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("avatar_path", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column(
                "updated_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "role IN ('jobseeker', 'recruiter', 'admin')",
                name="ck_users_role",
            ),
            sa.CheckConstraint(
                "account_status IN ('pending', 'approved', 'rejected')",
                name="ck_users_account_status",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )

    if not _table_exists("opportunities"):
        op.create_table(
            "opportunities",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("provider", sa.Text(), nullable=False),
            sa.Column("type", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("requirements", sa.Text(), nullable=False),
            sa.Column("official_link", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("required_skills", sa.Text(), nullable=False),
            sa.Column("location", sa.Text(), nullable=False),
            sa.Column("deadline", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("company_name", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column(
                "created_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "type IN ('internship', 'scholarship')",
                name="ck_opportunities_type",
            ),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("bookmarks"):
        op.create_table(
            "bookmarks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("opportunity_id", sa.Integer(), nullable=False),
            sa.Column(
                "saved_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "opportunity_id",
                name="uq_bookmarks_user_opportunity",
            ),
        )

    if not _table_exists("applications"):
        op.create_table(
            "applications",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("opportunity_id", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sa.Text(),
                server_default=sa.text("'Sudah Daftar'"),
                nullable=False,
            ),
            sa.Column("notes", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column(
                "applied_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "opportunity_id",
                name="uq_applications_user_opportunity",
            ),
        )

    if not _table_exists("documents"):
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("doc_type", sa.Text(), nullable=False),
            sa.Column("file_name", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("file_path", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("is_uploaded", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("notes", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column(
                "updated_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "doc_type", name="uq_documents_user_doc_type"),
        )

    if not _table_exists("chat_threads"):
        op.create_table(
            "chat_threads",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("participant_one_id", sa.Integer(), nullable=False),
            sa.Column("participant_two_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "participant_one_id <> participant_two_id",
                name="ck_chat_threads_distinct_participants",
            ),
            sa.ForeignKeyConstraint(["participant_one_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["participant_two_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "participant_one_id",
                "participant_two_id",
                name="uq_chat_threads_participants",
            ),
        )

    if not _table_exists("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("thread_id", sa.Integer(), nullable=False),
            sa.Column("sender_id", sa.Integer(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("attachment_path", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("attachment_type", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("attachment_name", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column(
                "created_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("target_type", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("metadata", sa.Text(), server_default=sa.text("'{}'"), nullable=True),
            sa.Column("ip_address", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column("user_agent", sa.Text(), server_default=sa.text("''"), nullable=True),
            sa.Column(
                "created_at",
                sa.Text(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    for index_name, table_name, columns in INDEXES:
        _create_index_if_missing(index_name, table_name, columns)


def downgrade():
    for index_name, table_name, _columns in reversed(INDEXES):
        _drop_index_if_exists(index_name, table_name)

    for table_name in (
        "audit_logs",
        "chat_messages",
        "chat_threads",
        "documents",
        "applications",
        "bookmarks",
        "opportunities",
        "users",
    ):
        _drop_table_if_exists(table_name)


INDEXES = (
    ("idx_users_role_account_status", "users", ["role", "account_status"]),
    ("idx_users_account_status", "users", ["account_status"]),
    (
        "idx_opportunities_created_by_updated_at",
        "opportunities",
        ["created_by", "updated_at"],
    ),
    ("idx_opportunities_type", "opportunities", ["type"]),
    ("idx_bookmarks_user_saved_at", "bookmarks", ["user_id", "saved_at"]),
    ("idx_bookmarks_opportunity_id", "bookmarks", ["opportunity_id"]),
    ("idx_applications_user_updated_at", "applications", ["user_id", "updated_at"]),
    ("idx_applications_opportunity_id", "applications", ["opportunity_id"]),
    ("idx_documents_user_uploaded", "documents", ["user_id", "is_uploaded"]),
    ("idx_chat_threads_participant_one", "chat_threads", ["participant_one_id"]),
    ("idx_chat_threads_participant_two", "chat_threads", ["participant_two_id"]),
    (
        "idx_chat_messages_thread_created_at",
        "chat_messages",
        ["thread_id", "created_at"],
    ),
    ("idx_chat_messages_sender_id", "chat_messages", ["sender_id"]),
    ("idx_audit_logs_user_created_at", "audit_logs", ["user_id", "created_at"]),
    ("idx_audit_logs_created_at_id", "audit_logs", ["created_at", "id"]),
    ("idx_audit_logs_action_created_at", "audit_logs", ["action", "created_at"]),
    ("idx_audit_logs_target", "audit_logs", ["target_type", "target_id"]),
)


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
