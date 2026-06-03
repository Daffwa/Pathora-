from collections.abc import Mapping

from sqlalchemy import func, select

from extensions import db
from models import ApplicationORM


class ApplicationListItem:
    def __init__(self, application):
        self.application_id = application.id
        self.status = application.status
        self.notes = application.notes
        self.applied_at = application.applied_at
        self.updated_at = application.updated_at
        self.opportunity_id = application.opportunity.id
        self.title = application.opportunity.title
        self.provider = application.opportunity.provider
        self.type = application.opportunity.type
        self.location = application.opportunity.location
        self.deadline = application.opportunity.deadline


APPLICATION_ROW_FIELDS = (
    "id",
    "user_id",
    "opportunity_id",
    "status",
    "notes",
    "applied_at",
    "updated_at",
)


class ApplicationRow(Mapping):
    def __init__(self, application):
        self._values = {
            field: getattr(application, field)
            for field in APPLICATION_ROW_FIELDS
        }

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


def as_application_row(application):
    if application is None:
        return None
    return ApplicationRow(application)


def find_by_user_and_opportunity(user_id, opportunity_id):
    return db.session.execute(
        select(ApplicationORM).where(
            ApplicationORM.user_id == user_id,
            ApplicationORM.opportunity_id == opportunity_id,
        )
    ).scalar_one_or_none()


def find_by_user_and_id(user_id, application_id):
    return db.session.execute(
        select(ApplicationORM).where(
            ApplicationORM.id == application_id,
            ApplicationORM.user_id == user_id,
        )
    ).scalar_one_or_none()


def find_row_by_user_and_id(user_id, application_id):
    return as_application_row(find_by_user_and_id(user_id, application_id))


def list_by_user(user_id):
    return db.session.execute(
        select(ApplicationORM)
        .where(ApplicationORM.user_id == user_id)
        .order_by(ApplicationORM.updated_at.desc())
    ).scalars().all()


def count_by_user(user_id):
    return db.session.execute(
        select(func.count())
        .select_from(ApplicationORM)
        .where(ApplicationORM.user_id == user_id)
    ).scalar_one()


def list_with_opportunity_by_user(user_id):
    applications = db.session.execute(
        select(ApplicationORM)
        .where(ApplicationORM.user_id == user_id)
        .order_by(ApplicationORM.updated_at.desc())
    ).scalars().all()
    return [ApplicationListItem(application) for application in applications]


def list_recent_with_opportunity_by_user(user_id, limit=3):
    applications = db.session.execute(
        select(ApplicationORM)
        .where(ApplicationORM.user_id == user_id)
        .order_by(ApplicationORM.updated_at.desc())
        .limit(limit)
    ).scalars().all()
    return [ApplicationListItem(application) for application in applications]


def create_application(
    *,
    user_id,
    opportunity_id,
    status="Sudah Daftar",
    notes="",
    commit=True,
):
    application = ApplicationORM(
        user_id=user_id,
        opportunity_id=opportunity_id,
        status=status,
        notes=notes,
    )
    db.session.add(application)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return application


def update_status(application_id, status, notes=None, commit=True):
    application = db.session.get(ApplicationORM, application_id)
    if application is None:
        return None

    application.status = status
    if notes is not None:
        application.notes = notes
    application.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return application


def delete_by_user_and_id(user_id, application_id, commit=True):
    application = find_by_user_and_id(user_id, application_id)
    if application is None:
        return 0

    db.session.delete(application)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return 1
