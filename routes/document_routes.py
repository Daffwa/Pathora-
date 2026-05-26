import sqlite3
from pathlib import Path

from flask import abort, flash, redirect, render_template, request, send_from_directory, session, url_for

from models.document import Document
from services.audit_service import record_audit_event
from services.auth_service import jobseeker_required_decorator
from services.constants import DOCUMENT_TYPES
from services.database_service import get_db
from services.document_service import get_document_for_user
from services.storage_service import (
    delete_file_if_exists,
    make_document_filename,
    save_uploaded_file,
    secure_upload_filename,
    validate_document_upload,
)


def register(app):
    @app.route("/documents")
    @jobseeker_required_decorator
    def documents():
        rows = get_db().execute(
            """
            SELECT * FROM documents
            WHERE user_id = ?
            """,
            (session["user_id"],),
        ).fetchall()
        document_by_type = {row["doc_type"]: Document.from_row(row, session["user_id"]) for row in rows}

        documents_list = []
        for doc_type in DOCUMENT_TYPES:
            document = document_by_type.get(
                doc_type,
                Document(
                    document_id=None,
                    user_id=session["user_id"],
                    doc_type=doc_type,
                ),
            )
            documents_list.append(document)

        complete_count = sum(1 for document in documents_list if document.is_complete())

        return render_template(
            "documents.html",
            documents=documents_list,
            complete_count=complete_count,
            total_count=len(DOCUMENT_TYPES),
        )


    @app.route("/documents/<path:doc_type>/update", methods=["POST"])
    @jobseeker_required_decorator
    def update_document(doc_type):
        if doc_type not in DOCUMENT_TYPES:
            abort(404)

        notes = request.form.get("notes", "").strip()
        uploaded_file = request.files.get("document_file")

        existing_document = get_document_for_user(doc_type)

        file_name = existing_document["file_name"] if existing_document else ""
        file_path = existing_document["file_path"] if existing_document else ""
        is_uploaded = 1 if request.form.get("is_uploaded") == "on" else 0

        if uploaded_file and uploaded_file.filename:
            if not validate_document_upload(uploaded_file):
                flash("Format file tidak didukung. Gunakan PDF, DOC, DOCX, PNG, JPG, atau JPEG.")
                return redirect(url_for("documents"))

            original_file_name = secure_upload_filename(uploaded_file.filename)
            saved_file_name = make_document_filename(
                session["user_id"], doc_type, original_file_name
            )
            save_uploaded_file(
                uploaded_file,
                app.config["UPLOAD_FOLDER"],
                saved_file_name,
            )

            if existing_document and existing_document["file_path"] != saved_file_name:
                delete_file_if_exists(app.config["UPLOAD_FOLDER"], existing_document["file_path"])

            file_name = original_file_name
            file_path = saved_file_name
            is_uploaded = 1

        try:
            get_db().execute(
                """
                INSERT INTO documents (user_id, doc_type, file_name, file_path, is_uploaded, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, doc_type) DO UPDATE SET
                    file_name = excluded.file_name,
                    file_path = excluded.file_path,
                    is_uploaded = excluded.is_uploaded,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session["user_id"], doc_type, file_name, file_path, is_uploaded, notes),
            )
            get_db().commit()
            if uploaded_file and uploaded_file.filename:
                record_audit_event(
                    "document.upload",
                    target_type="document",
                    metadata={"doc_type": doc_type, "file_name": file_name},
                )
            flash(f"Dokumen {doc_type} berhasil diperbarui.")
        except sqlite3.Error:
            flash("Dokumen belum bisa diperbarui. Silakan coba lagi.")

        return redirect(url_for("documents"))


    @app.route("/documents/<path:doc_type>/reset", methods=["POST"])
    @jobseeker_required_decorator
    def reset_document(doc_type):
        if doc_type not in DOCUMENT_TYPES:
            abort(404)

        existing_document = get_document_for_user(doc_type)

        try:
            if existing_document:
                delete_file_if_exists(app.config["UPLOAD_FOLDER"], existing_document["file_path"])

            get_db().execute(
                """
                INSERT INTO documents (user_id, doc_type, file_name, file_path, is_uploaded, notes)
                VALUES (?, ?, '', '', 0, '')
                ON CONFLICT(user_id, doc_type) DO UPDATE SET
                    file_name = '',
                    file_path = '',
                    is_uploaded = 0,
                    notes = '',
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session["user_id"], doc_type),
            )
            get_db().commit()
            flash(f"Dokumen {doc_type} berhasil di-reset.")
        except sqlite3.Error:
            flash("Dokumen belum bisa di-reset. Silakan coba lagi.")

        return redirect(url_for("documents"))


    @app.route("/documents/<path:doc_type>/download")
    @jobseeker_required_decorator
    def download_document(doc_type):
        if doc_type not in DOCUMENT_TYPES:
            abort(404)

        document = get_document_for_user(doc_type)

        if document is None or not document["file_path"]:
            flash("File dokumen belum tersedia.")
            return redirect(url_for("documents"))

        file_path = Path(app.config["UPLOAD_FOLDER"]) / document["file_path"]
        if not file_path.exists():
            flash("File dokumen tidak ditemukan di folder upload.")
            return redirect(url_for("documents"))

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            document["file_path"],
            as_attachment=False,
            download_name=document["file_name"],
        )
