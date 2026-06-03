from collections.abc import Mapping

from sqlalchemy import and_, func, or_, select

from extensions import db
from models import ApplicationORM, BookmarkORM, OpportunityORM


OPPORTUNITY_FIELDS = {
    "title",
    "provider",
    "type",
    "description",
    "requirements",
    "official_link",
    "required_skills",
    "location",
    "deadline",
    "created_by",
    "company_name",
}


OPPORTUNITY_ROW_FIELDS = (
    "id",
    "title",
    "provider",
    "type",
    "description",
    "requirements",
    "official_link",
    "required_skills",
    "location",
    "deadline",
    "created_by",
    "company_name",
    "created_at",
    "updated_at",
)


class OpportunityRow(Mapping):
    def __init__(self, opportunity, **extra):
        self._values = {
            field: getattr(opportunity, field)
            for field in OPPORTUNITY_ROW_FIELDS
        }
        self._values.update(extra)

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __getattr__(self, name):
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def as_opportunity_row(opportunity, **extra):
    if opportunity is None:
        return None
    return OpportunityRow(opportunity, **extra)


def find_by_id(opportunity_id):
    if opportunity_id is None:
        return None
    return db.session.get(OpportunityORM, opportunity_id)


def find_row_by_id(opportunity_id):
    return as_opportunity_row(find_by_id(opportunity_id))


def list_all():
    return db.session.execute(
        select(OpportunityORM).order_by(OpportunityORM.deadline.asc())
    ).scalars().all()


def list_all_rows():
    return [as_opportunity_row(opportunity) for opportunity in list_all()]


def list_by_creator(creator_id):
    return db.session.execute(
        select(OpportunityORM)
        .where(OpportunityORM.created_by == creator_id)
        .order_by(OpportunityORM.deadline.asc())
    ).scalars().all()


def list_rows_by_creator(creator_id):
    return [
        as_opportunity_row(opportunity)
        for opportunity in list_by_creator(creator_id)
    ]


def search_opportunities(search_query="", opportunity_type="", location=""):
    filters = []
    if search_query:
        keyword = f"%{search_query}%"
        filters.append(
            or_(
                OpportunityORM.title.like(keyword),
                OpportunityORM.provider.like(keyword),
                OpportunityORM.location.like(keyword),
                OpportunityORM.description.like(keyword),
            )
        )

    if opportunity_type in {"internship", "scholarship"}:
        filters.append(OpportunityORM.type == opportunity_type)

    if location:
        filters.append(OpportunityORM.location.like(f"%{location}%"))

    query = select(OpportunityORM)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(OpportunityORM.deadline.asc())
    return db.session.execute(query).scalars().all()


def list_distinct_locations():
    return db.session.execute(
        select(OpportunityORM.location)
        .distinct()
        .order_by(OpportunityORM.location.asc())
    ).scalars().all()


def count_bookmarks_by_user(user_id):
    return db.session.execute(
        select(func.count())
        .select_from(BookmarkORM)
        .where(BookmarkORM.user_id == user_id)
    ).scalar_one()


def add_bookmark(user_id, opportunity_id, commit=True):
    bookmark = BookmarkORM(user_id=user_id, opportunity_id=opportunity_id)
    db.session.add(bookmark)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return bookmark


def remove_bookmark(user_id, opportunity_id, commit=True):
    deleted_count = db.session.query(BookmarkORM).filter(
        BookmarkORM.user_id == user_id,
        BookmarkORM.opportunity_id == opportunity_id,
    ).delete(synchronize_session=False)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return deleted_count


def list_recent_saved_rows_by_user(user_id, limit=3):
    rows = db.session.execute(
        select(BookmarkORM, OpportunityORM)
        .join(OpportunityORM, OpportunityORM.id == BookmarkORM.opportunity_id)
        .where(BookmarkORM.user_id == user_id)
        .order_by(BookmarkORM.saved_at.desc())
        .limit(limit)
    ).all()
    return [
        as_opportunity_row(opportunity, saved_at=bookmark.saved_at)
        for bookmark, opportunity in rows
    ]


def list_bookmarks_by_user(user_id):
    rows = db.session.execute(
        select(BookmarkORM, OpportunityORM, ApplicationORM.status)
        .join(OpportunityORM, OpportunityORM.id == BookmarkORM.opportunity_id)
        .outerjoin(
            ApplicationORM,
            and_(
                ApplicationORM.opportunity_id == OpportunityORM.id,
                ApplicationORM.user_id == BookmarkORM.user_id,
            ),
        )
        .where(BookmarkORM.user_id == user_id)
        .order_by(BookmarkORM.saved_at.desc())
    ).all()
    return [
        as_opportunity_row(
            opportunity,
            saved_at=bookmark.saved_at,
            application_status=application_status or "",
        )
        for bookmark, opportunity, application_status in rows
    ]


def list_related_to_user(user_id):
    opportunities = db.session.execute(
        select(OpportunityORM)
        .outerjoin(BookmarkORM, BookmarkORM.opportunity_id == OpportunityORM.id)
        .outerjoin(ApplicationORM, ApplicationORM.opportunity_id == OpportunityORM.id)
        .where(or_(BookmarkORM.user_id == user_id, ApplicationORM.user_id == user_id))
        .distinct()
    ).scalars().all()
    return opportunities


def create_opportunity(data, commit=True, **overrides):
    payload = _filtered_payload(data)
    payload.update(_filtered_payload(overrides))
    opportunity = OpportunityORM(**payload)
    db.session.add(opportunity)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return opportunity


def update_opportunity(opportunity_id, data, creator_id=None, commit=True, **overrides):
    query = select(OpportunityORM).where(OpportunityORM.id == opportunity_id)
    if creator_id is not None:
        query = query.where(OpportunityORM.created_by == creator_id)

    opportunity = db.session.execute(query).scalar_one_or_none()
    if opportunity is None:
        return None

    payload = _filtered_payload(data)
    payload.update(_filtered_payload(overrides))
    for field, value in payload.items():
        if field != "created_by":
            setattr(opportunity, field, value)
    opportunity.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return opportunity


def delete_opportunity(opportunity_id, creator_id=None, commit=True):
    opportunity = find_by_id(opportunity_id)
    if opportunity is None:
        return 0
    if creator_id is not None and opportunity.created_by != creator_id:
        return 0

    db.session.query(BookmarkORM).filter(
        BookmarkORM.opportunity_id == opportunity_id
    ).delete(synchronize_session=False)
    db.session.query(ApplicationORM).filter(
        ApplicationORM.opportunity_id == opportunity_id
    ).delete(synchronize_session=False)
    db.session.delete(opportunity)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return 1


def _filtered_payload(data):
    if data is None:
        return {}
    return {key: value for key, value in dict(data).items() if key in OPPORTUNITY_FIELDS}
