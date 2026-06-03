from collections.abc import Mapping

from sqlalchemy import func, select

from extensions import db
from models import DocumentORM


DOCUMENT_ROW_FIELDS = (
    "id",
    "user_id",
    "doc_type",
    "file_name",
    "file_path",
    "is_uploaded",
    "notes",
    "updated_at",
)


class DocumentRow(Mapping):
    def __init__(self, document):
        self._values = {
            field: getattr(document, field)
            for field in DOCUMENT_ROW_FIELDS
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


def as_document_row(document):
    if document is None:
        return None
    return DocumentRow(document)


def list_by_user(user_id):
    return db.session.execute(
        select(DocumentORM)
        .where(DocumentORM.user_id == user_id)
        .order_by(DocumentORM.doc_type.asc())
    ).scalars().all()


def list_rows_by_user(user_id):
    return [as_document_row(document) for document in list_by_user(user_id)]


def count_completed_by_user(user_id):
    return db.session.execute(
        select(func.count())
        .select_from(DocumentORM)
        .where(
            DocumentORM.user_id == user_id,
            DocumentORM.is_uploaded == 1,
        )
    ).scalar_one()


def get_by_user_and_type(user_id, doc_type):
    return db.session.execute(
        select(DocumentORM).where(
            DocumentORM.user_id == user_id,
            DocumentORM.doc_type == doc_type,
        )
    ).scalar_one_or_none()


def get_row_by_user_and_type(user_id, doc_type):
    return as_document_row(get_by_user_and_type(user_id, doc_type))


def upsert_document(
    *,
    user_id,
    doc_type,
    file_name="",
    file_path="",
    is_uploaded=False,
    notes="",
    commit=True,
):
    document = get_by_user_and_type(user_id, doc_type)
    if document is None:
        document = DocumentORM(user_id=user_id, doc_type=doc_type)
        db.session.add(document)

    document.file_name = file_name
    document.file_path = file_path
    document.is_uploaded = 1 if is_uploaded else 0
    document.notes = notes
    document.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return document
