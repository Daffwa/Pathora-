from flask import session

from models.document import Document
from services.constants import DOCUMENT_TYPES
from services.database_service import get_db


def get_document_for_user(doc_type):
    return get_db().execute(
        """
        SELECT * FROM documents
        WHERE user_id = ? AND doc_type = ?
        """,
        (session["user_id"], doc_type),
    ).fetchone()


def get_document_progress_for_user(user_id):
    rows = get_db().execute(
        """
        SELECT * FROM documents
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
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
