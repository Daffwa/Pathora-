from datetime import datetime
from time import sleep

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
from services.auth_service import get_current_user


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
        response = None
        for attempt in range(2):
            try:
                response = google_client.models.generate_content(
                    model=GOOGLE_MODEL,
                    contents=build_google_assistant_prompt(user_message),
                )
                break
            except Exception:
                if attempt == 0:
                    sleep(1)
                    continue
                raise

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
        if "user_id" not in session:
            return jsonify({"error": "Silakan login terlebih dahulu."}), 401

        if get_current_user() is None:
            session.clear()
            return jsonify({"error": "Sesi akun tidak ditemukan. Silakan login ulang."}), 401

        payload = request.get_json(silent=True) or {}
        user_message = (payload.get("message") or "").strip()

        answer, error, status = _validate_and_generate(user_message)
        if error:
            return jsonify({"error": error}), status
        return jsonify({"answer": answer})


    @app.route("/ai-assistant/chat", methods=["POST"])
    def ai_assistant_chat():
        if "user_id" not in session:
            return jsonify({"error": "Silakan login terlebih dahulu."}), 401

        if get_current_user() is None:
            session.clear()
            return jsonify({"error": "Sesi akun tidak ditemukan. Silakan login ulang."}), 401

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
