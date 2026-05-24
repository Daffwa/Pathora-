from datetime import datetime

from flask import current_app, jsonify, request, session

from services.ai_service import (
    GOOGLE_API_KEY,
    GOOGLE_MODEL,
    AI_ASSISTANT_GENERIC_ERROR,
    AI_ASSISTANT_MAX_MESSAGE_LENGTH,
    build_google_assistant_prompt,
    contains_sensitive_ai_content,
    genai,
    google_client,
    redact_sensitive_log_text,
)
from services.auth_service import get_current_role, get_current_user
from services.rate_limit_service import check_rate_limit


def _require_authenticated_user():
    if "user_id" not in session:
        return jsonify({"error": "Silakan login terlebih dahulu."}), 401

    if get_current_user() is None:
        session.clear()
        return jsonify({"error": "Sesi akun tidak ditemukan. Silakan login ulang."}), 401

    return None


def _require_admin_user():
    auth_error = _require_authenticated_user()
    if auth_error is not None:
        return auth_error

    if get_current_role() != "admin":
        return jsonify({"error": "Akses ditolak."}), 403

    return None


def _require_ai_rate_limit():
    allowed, retry_after = check_rate_limit(
        "ai-assistant",
        current_app.config["AI_RATE_LIMIT"],
        current_app.config["AI_RATE_LIMIT_WINDOW_SECONDS"],
    )
    if allowed:
        return None

    response = jsonify(
        {
            "error": (
                "Terlalu banyak permintaan AI Assistant. "
                f"Coba lagi dalam {retry_after} detik."
            )
        }
    )
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def _validate_and_generate(user_message):
    if not user_message:
        return None, "Pesan tidak boleh kosong.", 400

    if len(user_message) > AI_ASSISTANT_MAX_MESSAGE_LENGTH:
        return None, "Pesan terlalu panjang. Maksimal 1000 karakter.", 400

    if contains_sensitive_ai_content(user_message):
        return None, (
            "Jangan kirim password, OTP, API key, atau data sensitif "
            "ke AI Assistant."
        ), 400

    if not GOOGLE_API_KEY or google_client is None:
        return None, "Konfigurasi AI Assistant belum tersedia.", 500

    try:
        response = google_client.models.generate_content(
            model=GOOGLE_MODEL,
            contents=build_google_assistant_prompt(user_message),
        )

        try:
            answer = (getattr(response, "text", "") or "").strip()
        except Exception as error:
            current_app.logger.warning(
                "Google AI Assistant response parse failed: %s: %s",
                error.__class__.__name__,
                redact_sensitive_log_text(error),
            )
            answer = ""

        if not answer:
            answer = "Maaf, saya belum bisa memberikan jawaban saat ini."

        return answer, None, None
    except Exception as error:
        current_app.logger.warning(
            "Google AI Assistant request failed: %s: %s",
            error.__class__.__name__,
            redact_sensitive_log_text(error),
        )
        return None, AI_ASSISTANT_GENERIC_ERROR, 500


def register(app):
    @app.get("/api/assistant/health")
    def api_assistant_health():
        auth_error = _require_admin_user()
        if auth_error is not None:
            return auth_error

        google_genai_imported = genai is not None
        api_key_configured = bool(GOOGLE_API_KEY)
        endpoint_ready = bool(
            google_genai_imported and api_key_configured and google_client is not None
        )
        return jsonify(
            {
                "google_genai_imported": google_genai_imported,
                "api_key_configured": api_key_configured,
                "model": GOOGLE_MODEL,
                "endpoint_ready": endpoint_ready,
            }
        )


    @app.post("/api/assistant")
    def api_assistant():
        auth_error = _require_authenticated_user()
        if auth_error is not None:
            return auth_error

        rate_limit_error = _require_ai_rate_limit()
        if rate_limit_error is not None:
            return rate_limit_error

        payload = request.get_json(silent=True) or {}
        user_message = (payload.get("message") or "").strip()

        answer, error, status = _validate_and_generate(user_message)
        if error:
            return jsonify({"error": error}), status
        return jsonify({"answer": answer})


    @app.route("/ai-assistant/chat", methods=["POST"])
    def ai_assistant_chat():
        auth_error = _require_authenticated_user()
        if auth_error is not None:
            return auth_error

        rate_limit_error = _require_ai_rate_limit()
        if rate_limit_error is not None:
            return rate_limit_error

        payload = request.get_json(silent=True) or {}
        user_message = (payload.get("message") or "").strip()

        answer, error, status = _validate_and_generate(user_message)
        if error:
            return jsonify({"error": error}), status

        return jsonify(
            {
                "answer": answer,
                "reply": answer,
                "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
            }
        )
