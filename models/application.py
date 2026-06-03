from sqlalchemy import Index, text

from extensions import db


class ApplicationORM(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("user_id", "opportunity_id", name="uq_applications_user_opportunity"),
        Index("idx_applications_user_updated_at", "user_id", "updated_at"),
        Index("idx_applications_opportunity_id", "opportunity_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer,
        db.ForeignKey("opportunities.id"),
        nullable=False,
    )
    status = db.Column(db.Text, nullable=False, server_default=text("'Sudah Daftar'"))
    notes = db.Column(db.Text, server_default=text("''"))
    applied_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship("UserORM", back_populates="applications")
    opportunity = db.relationship("OpportunityORM", back_populates="applications")
