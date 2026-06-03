from sqlalchemy import Index, text

from extensions import db


class DocumentORM(db.Model):
    __tablename__ = "documents"
    __table_args__ = (
        db.UniqueConstraint("user_id", "doc_type", name="uq_documents_user_doc_type"),
        Index("idx_documents_user_uploaded", "user_id", "is_uploaded"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doc_type = db.Column(db.Text, nullable=False)
    file_name = db.Column(db.Text, server_default=text("''"))
    file_path = db.Column(db.Text, server_default=text("''"))
    is_uploaded = db.Column(db.Integer, nullable=False, server_default=text("0"))
    notes = db.Column(db.Text, server_default=text("''"))
    updated_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship("UserORM", back_populates="documents")
