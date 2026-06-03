from extensions import db


class RateLimitBucketORM(db.Model):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        db.Index(
            "idx_rate_limit_scope_identifier_created",
            "scope",
            "identifier",
            "created_at_epoch",
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scope = db.Column(db.Text, nullable=False)
    identifier = db.Column(db.Text, nullable=False)
    created_at_epoch = db.Column(db.Float, nullable=False)
