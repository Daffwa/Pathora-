from flask import Blueprint, abort, current_app, flash, jsonify, render_template, request, send_from_directory, session
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.auth_service import (
    get_current_role,
    get_current_user,
    get_inactive_account_message,
    is_user_account_active,
    login_required,
)
from services.chat_service import (
    can_access_chat_attachment,
    chat_message_payload,
    create_chat_message,
    get_chat_contact_payload,
    get_chat_conversations,
    get_or_create_chat_thread_id,
    now_utc,
)
from services.constants import CHAT_MESSAGE_MAX_LENGTH
from services.recruiter_service import parse_positive_int
from services.rate_limit_service import check_rate_limit
from services.storage_service import (
    CHAT_IMAGE_MAX_BYTES,
    delete_file_if_exists,
    is_safe_stored_filename,
    make_chat_attachment_filename,
    save_uploaded_file,
    secure_upload_filename,
    validate_chat_image_upload,
)


bp = Blueprint("chat", __name__)

@bp.route("/uploads/chat/<path:filename>", endpoint="chat_attachment_file")
def chat_attachment_file(filename):
    if "user_id" not in session:
        abort(404)
    user = get_current_user()
    if user is None or not is_user_account_active(user):
        abort(404)

    if not is_safe_stored_filename(filename):
        abort(404)
    safe_filename = secure_upload_filename(filename)

    if not can_access_chat_attachment(safe_filename, session["user_id"]):
        abort(404)

    return send_from_directory(current_app.config["CHAT_UPLOAD_FOLDER"], safe_filename)


@bp.route("/chat", endpoint="chat")
@login_required
def chat():
    current_role = get_current_role()
    selected_contact_id = parse_positive_int(
        request.args.get("user_id")
        or request.args.get("contact_id")
        or request.args.get("contact")
    )
    conversations = get_chat_conversations(
        session["user_id"],
        current_role,
        selected_contact_id,
    )

    if selected_contact_id and not any(
        conversation["contactId"] == selected_contact_id
        for conversation in conversations
    ):
        flash("Kontak chat tidak ditemukan atau tidak dapat diakses.")
        selected_contact_id = None

    return render_template(
        "chat.html",
        chat_conversations=conversations,
        selected_contact_id=str(selected_contact_id) if selected_contact_id else "",
    )


@bp.route("/chat/messages", methods=["POST"], endpoint="send_chat_message")
def send_chat_message():
    if "user_id" not in session:
        return jsonify({"error": "Silakan login terlebih dahulu."}), 401
    user = get_current_user()
    if user is None:
        session.clear()
        return jsonify({"error": "Silakan login terlebih dahulu."}), 401
    if not is_user_account_active(user):
        return jsonify({"error": get_inactive_account_message(user)}), 403

    allowed, retry_after = check_rate_limit(
        "chat-message",
        current_app.config["CHAT_RATE_LIMIT"],
        current_app.config["CHAT_RATE_LIMIT_WINDOW_SECONDS"],
    )
    if not allowed:
        response = jsonify(
            {
                "error": (
                    "Terlalu banyak pesan dikirim. "
                    f"Coba lagi dalam {retry_after} detik."
                )
            }
        )
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    current_role = get_current_role()
    payload = request.get_json(silent=True) or {}
    form_data = request.form or {}
    contact_id = parse_positive_int(
        payload.get("contact_id") or form_data.get("contact_id")
    )
    message = (payload.get("message") or form_data.get("message") or "").strip()
    uploaded_image = (
        request.files.get("image")
        or request.files.get("attachment")
        or request.files.get("file")
    )

    if contact_id is None:
        return jsonify({"error": "Kontak chat tidak valid."}), 400
    if not message and (uploaded_image is None or not uploaded_image.filename):
        return jsonify({"error": "Pesan atau gambar wajib diisi."}), 400
    if len(message) > CHAT_MESSAGE_MAX_LENGTH:
        return jsonify({"error": "Pesan terlalu panjang."}), 400
    if uploaded_image and uploaded_image.filename:
        is_valid_image, image_error = validate_chat_image_upload(
            uploaded_image,
            CHAT_IMAGE_MAX_BYTES,
        )
        if not is_valid_image:
            return jsonify({"error": image_error}), 400

    contact = get_chat_contact_payload(session["user_id"], current_role, contact_id)
    if contact is None:
        return jsonify({"error": "Kontak chat tidak ditemukan atau tidak dapat diakses."}), 403

    attachment_path = ""
    attachment_type = ""
    attachment_name = ""

    if uploaded_image and uploaded_image.filename:
        attachment_path = make_chat_attachment_filename(
            session["user_id"],
            uploaded_image.filename,
        )
        attachment_type = "image"
        attachment_name = secure_upload_filename(uploaded_image.filename) or "gambar"
        try:
            save_uploaded_file(
                uploaded_image,
                current_app.config["CHAT_UPLOAD_FOLDER"],
                attachment_path,
            )
        except (OSError, ValueError):
            return jsonify({"error": "Gambar belum bisa diunggah. Silakan coba lagi."}), 500

    try:
        thread_id = get_or_create_chat_thread_id(session["user_id"], contact_id)
        created_at = now_utc().isoformat(timespec="seconds")
        saved_message = create_chat_message(
            thread_id=thread_id,
            sender_id=session["user_id"],
            body=message,
            attachment_path=attachment_path,
            attachment_type=attachment_type,
            attachment_name=attachment_name,
            created_at=created_at,
        )
    except SQLAlchemyError:
        db.session.rollback()
        if attachment_path:
            delete_file_if_exists(current_app.config["CHAT_UPLOAD_FOLDER"], attachment_path)
        return jsonify({"error": "Pesan belum bisa dikirim. Silakan coba lagi."}), 500

    return jsonify(
        {
            "thread_id": thread_id,
            "message": chat_message_payload(saved_message, session["user_id"]),
        }
    )
