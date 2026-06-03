from sqlalchemy import Index, text

from extensions import db


class AuditLogORM(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_user_created_at", "user_id", "created_at"),
        Index("idx_audit_logs_created_at_id", "created_at", "id"),
        Index("idx_audit_logs_action_created_at", "action", "created_at"),
        Index("idx_audit_logs_target", "target_type", "target_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.Text, server_default=text("''"))
    target_id = db.Column(db.Integer)
    metadata_json = db.Column("metadata", db.Text, server_default=text("'{}'"))
    ip_address = db.Column(db.Text, server_default=text("''"))
    user_agent = db.Column(db.Text, server_default=text("''"))
    created_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship("UserORM", back_populates="audit_logs")
