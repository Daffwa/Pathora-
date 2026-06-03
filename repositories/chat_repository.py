from collections.abc import Mapping

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import (
    ApplicationORM,
    ChatMessageORM,
    ChatThreadORM,
    OpportunityORM,
    UserORM,
)


CHAT_MESSAGE_FIELDS = (
    "id",
    "sender_id",
    "body",
    "attachment_path",
    "attachment_type",
    "attachment_name",
    "created_at",
)

CONTACT_FIELDS = (
    "id",
    "name",
    "email",
    "role",
    "company_name",
    "company_position",
)


class ChatRow(Mapping):
    def __init__(self, values):
        self._values = dict(values)

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


def chat_pair(user_id, contact_id):
    return tuple(sorted((int(user_id), int(contact_id))))


def as_message_row(message):
    if message is None:
        return None
    return ChatRow({field: getattr(message, field) for field in CHAT_MESSAGE_FIELDS})


def as_contact_row(user):
    if user is None:
        return None
    return ChatRow({field: getattr(user, field) for field in CONTACT_FIELDS})


def as_relation_row(application, opportunity):
    if application is None or opportunity is None:
        return None
    return ChatRow(
        {
            "status": application.status,
            "updated_at": application.updated_at,
            "opportunity_title": opportunity.title,
            "opportunity_provider": opportunity.provider,
        }
    )


def as_contact_relation_row(contact, application, opportunity):
    values = dict(as_contact_row(contact))
    values.update(dict(as_relation_row(application, opportunity)))
    return ChatRow(values)


def find_thread_id(user_id, contact_id):
    participant_one_id, participant_two_id = chat_pair(user_id, contact_id)
    return db.session.execute(
        select(ChatThreadORM.id).where(
            ChatThreadORM.participant_one_id == participant_one_id,
            ChatThreadORM.participant_two_id == participant_two_id,
        )
    ).scalar_one_or_none()


def get_or_create_thread_id(user_id, contact_id):
    thread_id = find_thread_id(user_id, contact_id)
    if thread_id is not None:
        return thread_id

    participant_one_id, participant_two_id = chat_pair(user_id, contact_id)
    thread = ChatThreadORM(
        participant_one_id=participant_one_id,
        participant_two_id=participant_two_id,
    )
    db.session.add(thread)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return find_thread_id(user_id, contact_id)
    return thread.id


def list_messages(thread_id):
    if thread_id is None:
        return []

    messages = db.session.execute(
        select(ChatMessageORM)
        .where(ChatMessageORM.thread_id == thread_id)
        .order_by(ChatMessageORM.created_at.asc(), ChatMessageORM.id.asc())
    ).scalars().all()
    return [as_message_row(message) for message in messages]


def create_message(
    *,
    thread_id,
    sender_id,
    body,
    attachment_path="",
    attachment_type="",
    attachment_name="",
    created_at,
    commit=True,
):
    message = ChatMessageORM(
        thread_id=thread_id,
        sender_id=sender_id,
        body=body or "",
        attachment_path=attachment_path or "",
        attachment_type=attachment_type or "",
        attachment_name=attachment_name or "",
        created_at=created_at,
    )
    db.session.add(message)
    db.session.flush()
    row = as_message_row(message)
    if commit:
        db.session.commit()
    return row


def update_thread_timestamp(thread_id, updated_at, commit=True):
    thread = db.session.get(ChatThreadORM, thread_id)
    if thread is None:
        return None

    thread.updated_at = updated_at
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return thread


def create_message_and_touch_thread(
    *,
    thread_id,
    sender_id,
    body,
    attachment_path="",
    attachment_type="",
    attachment_name="",
    created_at,
    commit=True,
):
    message = ChatMessageORM(
        thread_id=thread_id,
        sender_id=sender_id,
        body=body or "",
        attachment_path=attachment_path or "",
        attachment_type=attachment_type or "",
        attachment_name=attachment_name or "",
        created_at=created_at,
    )
    db.session.add(message)

    thread = db.session.get(ChatThreadORM, thread_id)
    if thread is not None:
        thread.updated_at = created_at

    db.session.flush()
    row = as_message_row(message)
    if commit:
        db.session.commit()
    return row


def find_contact(contact_id):
    return as_contact_row(db.session.get(UserORM, contact_id))


def find_recruiter_relation(recruiter_id, applicant_id):
    row = db.session.execute(
        select(ApplicationORM, OpportunityORM)
        .join(OpportunityORM, OpportunityORM.id == ApplicationORM.opportunity_id)
        .where(
            ApplicationORM.user_id == applicant_id,
            OpportunityORM.created_by == recruiter_id,
        )
        .order_by(ApplicationORM.updated_at.desc(), ApplicationORM.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    application, opportunity = row
    return as_relation_row(application, opportunity)


def find_jobseeker_relation(jobseeker_id, recruiter_id):
    return find_recruiter_relation(recruiter_id, jobseeker_id)


def list_relation_rows(current_user_id, current_role):
    if current_role == "recruiter":
        rows = db.session.execute(
            select(UserORM, ApplicationORM, OpportunityORM)
            .join(OpportunityORM, OpportunityORM.id == ApplicationORM.opportunity_id)
            .join(UserORM, UserORM.id == ApplicationORM.user_id)
            .where(OpportunityORM.created_by == current_user_id)
            .order_by(ApplicationORM.updated_at.desc(), ApplicationORM.id.desc())
        ).all()
        return [
            as_contact_relation_row(contact, application, opportunity)
            for contact, application, opportunity in rows
        ]

    if current_role == "jobseeker":
        rows = db.session.execute(
            select(UserORM, ApplicationORM, OpportunityORM)
            .join(OpportunityORM, OpportunityORM.id == ApplicationORM.opportunity_id)
            .join(UserORM, UserORM.id == OpportunityORM.created_by)
            .where(
                ApplicationORM.user_id == current_user_id,
                OpportunityORM.created_by.is_not(None),
            )
            .order_by(ApplicationORM.updated_at.desc(), ApplicationORM.id.desc())
        ).all()
        return [
            as_contact_relation_row(contact, application, opportunity)
            for contact, application, opportunity in rows
        ]

    return []


def attachment_exists_for_user(attachment_path, user_id):
    return db.session.execute(
        select(ChatMessageORM.id)
        .join(ChatThreadORM, ChatThreadORM.id == ChatMessageORM.thread_id)
        .where(
            ChatMessageORM.attachment_path == attachment_path,
            or_(
                ChatThreadORM.participant_one_id == user_id,
                ChatThreadORM.participant_two_id == user_id,
            ),
        )
        .limit(1)
    ).first() is not None
