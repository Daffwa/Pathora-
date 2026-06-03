from sqlalchemy import CheckConstraint, Index, text

from extensions import db


class OpportunityORM(db.Model):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "type IN ('internship', 'scholarship')",
            name="ck_opportunities_type",
        ),
        Index(
            "idx_opportunities_created_by_updated_at",
            "created_by",
            "updated_at",
        ),
        Index("idx_opportunities_type", "type"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    provider = db.Column(db.Text, nullable=False)
    type = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    official_link = db.Column(db.Text, server_default=text("''"))
    required_skills = db.Column(db.Text, nullable=False)
    location = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    company_name = db.Column(db.Text, server_default=text("''"))
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

    creator = db.relationship(
        "UserORM",
        back_populates="created_opportunities",
        foreign_keys=[created_by],
    )
    bookmarks = db.relationship("BookmarkORM", back_populates="opportunity")
    applications = db.relationship("ApplicationORM", back_populates="opportunity")
