from flask import session

from dto.document import Document
from repositories import document_repository
from services.constants import DOCUMENT_TYPES


def get_document_for_user(doc_type):
    return document_repository.get_row_by_user_and_type(session["user_id"], doc_type)


def get_document_progress_for_user(user_id):
    rows = document_repository.list_rows_by_user(user_id)
    document_by_type = {row["doc_type"]: Document.from_row(row, user_id) for row in rows}

    documents = []
    for doc_type in DOCUMENT_TYPES:
        documents.append(
            document_by_type.get(
                doc_type,
                Document(document_id=None, user_id=user_id, doc_type=doc_type),
            )
        )

    complete_count = sum(1 for document in documents if document.is_complete())
    total_count = len(DOCUMENT_TYPES)
    percent = round((complete_count / total_count) * 100) if total_count else 0

    return {
        "documents": documents,
        "complete_count": complete_count,
        "total_count": total_count,
        "percent": percent,
    }
