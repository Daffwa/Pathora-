from sqlalchemy import CheckConstraint, Index, text

from extensions import db


class ChatThreadORM(db.Model):
    __tablename__ = "chat_threads"
    __table_args__ = (
        db.UniqueConstraint(
            "participant_one_id",
            "participant_two_id",
            name="uq_chat_threads_participants",
        ),
        CheckConstraint(
            "participant_one_id <> participant_two_id",
            name="ck_chat_threads_distinct_participants",
        ),
        Index("idx_chat_threads_participant_one", "participant_one_id"),
        Index("idx_chat_threads_participant_two", "participant_two_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    participant_one_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    participant_two_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    participant_one = db.relationship(
        "UserORM",
        back_populates="chat_threads_as_participant_one",
        foreign_keys=[participant_one_id],
    )
    participant_two = db.relationship(
        "UserORM",
        back_populates="chat_threads_as_participant_two",
        foreign_keys=[participant_two_id],
    )
    messages = db.relationship("ChatMessageORM", back_populates="thread")


class ChatMessageORM(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_messages_thread_created_at", "thread_id", "created_at"),
        Index("idx_chat_messages_sender_id", "sender_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("chat_threads.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.Text, server_default=text("''"))
    attachment_type = db.Column(db.Text, server_default=text("''"))
    attachment_name = db.Column(db.Text, server_default=text("''"))
    created_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    thread = db.relationship("ChatThreadORM", back_populates="messages")
    sender = db.relationship("UserORM", back_populates="sent_chat_messages")
