from sqlalchemy import Index, text

from extensions import db


class BookmarkORM(db.Model):
    __tablename__ = "bookmarks"
    __table_args__ = (
        db.UniqueConstraint("user_id", "opportunity_id", name="uq_bookmarks_user_opportunity"),
        Index("idx_bookmarks_user_saved_at", "user_id", "saved_at"),
        Index("idx_bookmarks_opportunity_id", "opportunity_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer,
        db.ForeignKey("opportunities.id"),
        nullable=False,
    )
    saved_at = db.Column(
        db.Text,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship("UserORM", back_populates="bookmarks")
    opportunity = db.relationship("OpportunityORM", back_populates="bookmarks")
