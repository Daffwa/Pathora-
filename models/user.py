from sqlalchemy import CheckConstraint, Index, text

from extensions import db


class UserORM(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('jobseeker', 'recruiter', 'admin')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "account_status IN ('pending', 'approved', 'rejected')",
            name="ck_users_account_status",
        ),
        Index("idx_users_role_account_status", "role", "account_status"),
        Index("idx_users_account_status", "account_status"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, server_default=text("'jobseeker'"))
    account_status = db.Column(db.Text, nullable=False, server_default=text("'approved'"))
    skills = db.Column(db.Text, server_default=text("''"))
    company_name = db.Column(db.Text, server_default=text("''"))
    company_position = db.Column(db.Text, server_default=text("''"))
    nickname = db.Column(db.Text, server_default=text("''"))
    phone = db.Column(db.Text, server_default=text("''"))
    birth_date = db.Column(db.Text, server_default=text("''"))
    gender = db.Column(db.Text, server_default=text("''"))
    domicile = db.Column(db.Text, server_default=text("''"))
    bio = db.Column(db.Text, server_default=text("''"))
    university = db.Column(db.Text, server_default=text("''"))
    faculty = db.Column(db.Text, server_default=text("''"))
    major = db.Column(db.Text, server_default=text("''"))
    degree = db.Column(db.Text, server_default=text("''"))
    semester = db.Column(db.Text, server_default=text("''"))
    gpa = db.Column(db.Text, server_default=text("''"))
    entry_year = db.Column(db.Text, server_default=text("''"))
    desired_positions = db.Column(db.Text, server_default=text("''"))
    preferred_program = db.Column(db.Text, server_default=text("''"))
    preferred_locations = db.Column(db.Text, server_default=text("''"))
    work_arrangement = db.Column(db.Text, server_default=text("''"))
    interests = db.Column(db.Text, server_default=text("''"))
    linkedin = db.Column(db.Text, server_default=text("''"))
    github = db.Column(db.Text, server_default=text("''"))
    portfolio_url = db.Column(db.Text, server_default=text("''"))
    avatar_path = db.Column(db.Text, server_default=text("''"))
    updated_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    created_opportunities = db.relationship(
        "OpportunityORM",
        back_populates="creator",
        foreign_keys="OpportunityORM.created_by",
    )
    bookmarks = db.relationship("BookmarkORM", back_populates="user")
    applications = db.relationship("ApplicationORM", back_populates="user")
    documents = db.relationship("DocumentORM", back_populates="user")
    sent_chat_messages = db.relationship("ChatMessageORM", back_populates="sender")
    audit_logs = db.relationship("AuditLogORM", back_populates="user")
    chat_threads_as_participant_one = db.relationship(
        "ChatThreadORM",
        back_populates="participant_one",
        foreign_keys="ChatThreadORM.participant_one_id",
    )
    chat_threads_as_participant_two = db.relationship(
        "ChatThreadORM",
        back_populates="participant_two",
        foreign_keys="ChatThreadORM.participant_two_id",
    )
