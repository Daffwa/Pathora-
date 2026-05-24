import os
import re

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

from services.constants import (
    AI_ASSISTANT_GENERIC_ERROR,
    AI_ASSISTANT_MAX_MESSAGE_LENGTH,
    AI_ASSISTANT_SYSTEM_PROMPT,
    GOOGLE_MODEL_DEFAULT,
    GOOGLE_TIMEOUT_DEFAULT_SECONDS,
)
def get_int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def redact_sensitive_log_text(value):
    text = str(value)
    replacements = [
        (r"AIza[0-9A-Za-z_-]{20,}", "<redacted-google-api-key>"),
        (r"sk-[A-Za-z0-9_-]{8,}", "<redacted-api-key>"),
        (r"nvapi-[A-Za-z0-9_-]{8,}", "<redacted-api-key>"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def create_google_client():
    if genai is None or not GOOGLE_API_KEY:
        return None

    http_options = None
    if genai_types is not None:
        http_options = genai_types.HttpOptions(
            timeout=GOOGLE_TIMEOUT_SECONDS * 1000
        )

    return genai.Client(api_key=GOOGLE_API_KEY, http_options=http_options)


GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
).strip()
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", GOOGLE_MODEL_DEFAULT).strip() or GOOGLE_MODEL_DEFAULT
GOOGLE_TIMEOUT_SECONDS = max(
    1,
    get_int_env("GOOGLE_TIMEOUT_SECONDS", GOOGLE_TIMEOUT_DEFAULT_SECONDS),
)
GOOGLE_CLIENT_INIT_ERROR = None
try:
    google_client = create_google_client()
except Exception as error:
    GOOGLE_CLIENT_INIT_ERROR = error
    google_client = None


def log_google_client_init_error(app):
    if GOOGLE_CLIENT_INIT_ERROR is None:
        return
    app.logger.warning(
        "Google AI Assistant client init failed: %s: %s",
        GOOGLE_CLIENT_INIT_ERROR.__class__.__name__,
        redact_sensitive_log_text(GOOGLE_CLIENT_INIT_ERROR),
    )


def contains_sensitive_ai_content(message):
    lowered = message.lower()
    sensitive_value_patterns = [
        r"\b(password|kata sandi|api[_\s-]?key|token|secret)\b\s*[:=]\s*\S+",
        r"\b(otp|kode otp|kode verifikasi)\b.{0,24}\d{4,8}\b",
        r"\b(sk-[A-Za-z0-9_-]{8,}|nvapi-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{20,})\b",
    ]

    if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in sensitive_value_patterns):
        return True

    sensitive_share_patterns = [
        r"\b(password|kata sandi|api[_\s-]?key|token|secret) saya\s+(adalah|=|:)\s+\S+",
        r"\b(otp|kode otp) saya\s+(adalah|=|:)?\s*\d{4,8}\b",
    ]
    return any(
        re.search(pattern, lowered, flags=re.IGNORECASE)
        for pattern in sensitive_share_patterns
    )


def build_local_assistant_reply(user_message):
    message = (user_message or "").lower()
    topics = [
        (
            ("daftar", "register", "akun"),
            (
                "Untuk daftar akun, buka halaman Daftar, pilih role Jobseeker "
                "atau Recruiter, isi data yang diminta, lalu submit form. "
                "Setelah berhasil, kamu akan langsung masuk ke dashboard."
            ),
        ),
        (
            ("login", "masuk"),
            (
                "Untuk login, buka halaman Masuk, isi email dan password, lalu "
                "tekan tombol masuk. Jika role akun valid, Pathora akan membuka "
                "dashboard sesuai role kamu."
            ),
        ),
        (
            ("apply", "lamar", "lamaran", "daftar peluang"),
            (
                "Untuk melamar atau melacak peluang, buka halaman Peluang, pilih "
                "detail peluang yang sesuai, lalu gunakan tombol lacak/daftar. "
                "Statusnya bisa dipantau dari halaman Pelacakan Lamaran."
            ),
        ),
        (
            ("dokumen", "upload", "cv", "transkrip", "sertifikat"),
            (
                "Untuk upload dokumen, buka Kelola Dokumen, pilih jenis dokumen, "
                "unggah file yang sesuai, lalu simpan. Dokumen yang lengkap ikut "
                "membantu skor prioritas kamu."
            ),
        ),
        (
            ("status", "tracking", "tracker", "progres"),
            (
                "Status lamaran bisa dicek di halaman Pelacakan Lamaran. Recruiter "
                "dapat memperbarui status seperti Sedang Direview, Interview, "
                "Diterima, atau Ditolak."
            ),
        ),
        (
            ("rekomendasi", "peluang", "skor", "priority", "prioritas"),
            (
                "Rekomendasi peluang diprioritaskan dari kecocokan skill, deadline, "
                "dan kesiapan dokumen. Lengkapi profil, skill, dan dokumen agar "
                "skor prioritas lebih akurat."
            ),
        ),
        (
            ("chat", "pesan", "recruiter"),
            (
                "Fitur chat dipakai untuk komunikasi antara jobseeker dan recruiter "
                "yang terhubung lewat lamaran. Buka menu Chat untuk melihat kontak "
                "yang tersedia."
            ),
        ),
    ]

    for keywords, reply in topics:
        if any(keyword in message for keyword in keywords):
            return reply

    return (
        "Saya siap membantu seputar Pathora: cara daftar, login, mencari peluang, "
        "melacak lamaran, upload dokumen, chat recruiter, dan meningkatkan skor "
        "prioritas. Coba tanyakan salah satu topik itu."
    )


def build_google_assistant_prompt(user_message):
    return f"{AI_ASSISTANT_SYSTEM_PROMPT}\n\nPertanyaan user:\n{user_message}"
