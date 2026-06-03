from pathlib import Path

from flask import abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from dto.document import Document
from extensions import db
from repositories import document_repository
from services.audit_service import record_audit_event
from services.auth_service import jobseeker_required_decorator
from services.constants import DOCUMENT_TYPES
from services.storage_service import (
    delete_file_if_exists,
    make_document_filename,
    save_uploaded_file,
    secure_upload_filename,
    validate_document_upload,
)


def _document_from_orm(document, user_id, doc_type=None):
    if document is None:
        return Document(document_id=None, user_id=user_id, doc_type=doc_type or "")

    return Document(
        document_id=document.id,
        user_id=document.user_id,
        doc_type=document.doc_type,
        file_name=document.file_name or "",
        file_path=document.file_path or "",
        is_uploaded=bool(document.is_uploaded),
        notes=document.notes or "",
    )


def register(app):
    @app.route("/documents")
    @jobseeker_required_decorator
    def documents():
        rows = document_repository.list_by_user(session["user_id"])
        document_by_type = {
            document.doc_type: _document_from_orm(document, session["user_id"])
            for document in rows
        }

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

        existing_document = document_repository.get_by_user_and_type(session["user_id"], doc_type)

        file_name = existing_document.file_name if existing_document else ""
        file_path = existing_document.file_path if existing_document else ""
        is_uploaded = 1 if request.form.get("is_uploaded") == "on" else 0

        if uploaded_file and uploaded_file.filename:
            if not validate_document_upload(uploaded_file):
                flash(
                    "Format file tidak didukung. Gunakan file PDF, DOC, DOCX, PNG, "
                    "JPG, atau JPEG yang valid."
                )
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

            if existing_document and existing_document.file_path != saved_file_name:
                delete_file_if_exists(app.config["UPLOAD_FOLDER"], existing_document.file_path)

            file_name = original_file_name
            file_path = saved_file_name
            is_uploaded = 1

        try:
            document_repository.upsert_document(
                user_id=session["user_id"],
                doc_type=doc_type,
                file_name=file_name,
                file_path=file_path,
                is_uploaded=bool(is_uploaded),
                notes=notes,
            )
            if uploaded_file and uploaded_file.filename:
                record_audit_event(
                    "document.upload",
                    target_type="document",
                    metadata={"doc_type": doc_type, "file_name": file_name},
                )
            flash(f"Dokumen {doc_type} berhasil diperbarui.")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Dokumen belum bisa diperbarui. Silakan coba lagi.")

        return redirect(url_for("documents"))


    @app.route("/documents/<path:doc_type>/reset", methods=["POST"])
    @jobseeker_required_decorator
    def reset_document(doc_type):
        if doc_type not in DOCUMENT_TYPES:
            abort(404)

        existing_document = document_repository.get_by_user_and_type(session["user_id"], doc_type)

        try:
            if existing_document:
                delete_file_if_exists(app.config["UPLOAD_FOLDER"], existing_document.file_path)

            document_repository.upsert_document(
                user_id=session["user_id"],
                doc_type=doc_type,
                file_name="",
                file_path="",
                is_uploaded=False,
                notes="",
            )
            flash(f"Dokumen {doc_type} berhasil di-reset.")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Dokumen belum bisa di-reset. Silakan coba lagi.")

        return redirect(url_for("documents"))


    @app.route("/documents/<path:doc_type>/download")
    @jobseeker_required_decorator
    def download_document(doc_type):
        if doc_type not in DOCUMENT_TYPES:
            abort(404)

        document = document_repository.get_by_user_and_type(session["user_id"], doc_type)

        if document is None or not document.file_path:
            flash("File dokumen belum tersedia.")
            return redirect(url_for("documents"))

        file_path = Path(app.config["UPLOAD_FOLDER"]) / document.file_path
        if not file_path.exists():
            flash("File dokumen tidak ditemukan di folder upload.")
            return redirect(url_for("documents"))

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            document.file_path,
            as_attachment=True,
            download_name=document.file_name,
        )
