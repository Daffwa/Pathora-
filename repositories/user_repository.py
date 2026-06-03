from collections.abc import Mapping

from sqlalchemy import func, select

from extensions import db
from models import UserORM


PROFILE_FIELDS = {
    "name",
    "skills",
    "company_name",
    "company_position",
    "nickname",
    "phone",
    "birth_date",
    "gender",
    "domicile",
    "bio",
    "university",
    "faculty",
    "major",
    "degree",
    "semester",
    "gpa",
    "entry_year",
    "desired_positions",
    "preferred_program",
    "preferred_locations",
    "work_arrangement",
    "interests",
    "linkedin",
    "github",
    "portfolio_url",
    "avatar_path",
}


USER_ROW_FIELDS = (
    "id",
    "name",
    "email",
    "password_hash",
    "role",
    "account_status",
    "skills",
    "company_name",
    "company_position",
    "nickname",
    "phone",
    "birth_date",
    "gender",
    "domicile",
    "bio",
    "university",
    "faculty",
    "major",
    "degree",
    "semester",
    "gpa",
    "entry_year",
    "desired_positions",
    "preferred_program",
    "preferred_locations",
    "work_arrangement",
    "interests",
    "linkedin",
    "github",
    "portfolio_url",
    "avatar_path",
    "updated_at",
    "created_at",
)


PROFILE_UPDATE_FIELDS = PROFILE_FIELDS | {"email", "password_hash"}


class UserRow(Mapping):
    def __init__(self, user):
        self._values = {field: getattr(user, field) for field in USER_ROW_FIELDS}

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


def as_user_row(user):
    if user is None:
        return None
    return UserRow(user)


def find_by_id(user_id):
    if user_id is None:
        return None
    return db.session.get(UserORM, user_id)


def find_row_by_id(user_id):
    return as_user_row(find_by_id(user_id))


def find_by_email(email):
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None
    return db.session.execute(
        select(UserORM).where(UserORM.email == normalized_email)
    ).scalar_one_or_none()


def find_by_id_and_email(user_id, email):
    normalized_email = _normalize_email(email)
    if not user_id or not normalized_email:
        return None
    return db.session.execute(
        select(UserORM).where(
            UserORM.id == user_id,
            UserORM.email == normalized_email,
        )
    ).scalar_one_or_none()


def email_exists(email, exclude_user_id=None):
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return False

    query = select(UserORM.id).where(UserORM.email == normalized_email)
    if exclude_user_id is not None:
        query = query.where(UserORM.id != exclude_user_id)
    return db.session.execute(query).first() is not None


def create_user(
    *,
    name,
    email,
    password_hash,
    role="jobseeker",
    account_status="approved",
    skills="",
    company_name="",
    company_position="",
    commit=True,
    **profile_fields,
):
    user = UserORM(
        name=name,
        email=_normalize_email(email),
        password_hash=password_hash,
        role=role,
        account_status=account_status,
        skills=skills,
        company_name=company_name,
        company_position=company_position,
    )
    _apply_profile_fields(user, profile_fields)
    db.session.add(user)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return user


def update_user_password(user_id, password_hash, commit=True):
    user = find_by_id(user_id)
    if user is None:
        return None

    user.password_hash = password_hash
    user.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return user


def update_user_profile_basic(user_id, commit=True, **fields):
    user = find_by_id(user_id)
    if user is None:
        return None

    _apply_profile_fields(user, fields)
    user.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return user


def update_profile(user_id, fields, commit=True):
    user = find_by_id(user_id)
    if user is None:
        return None

    for field, value in fields.items():
        if field in PROFILE_UPDATE_FIELDS:
            if field == "email":
                value = _normalize_email(value)
            setattr(user, field, value)
    user.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return user


def _apply_profile_fields(user, fields):
    for field, value in fields.items():
        if field in PROFILE_FIELDS:
            setattr(user, field, value)


def _normalize_email(email):
    return (email or "").strip().lower()
