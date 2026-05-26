import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage


REQUIRED_MAIL_ENV = (
    "MAIL_SERVER",
    "MAIL_PORT",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_DEFAULT_SENDER",
)


class MailConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MailConfig:
    server: str
    port: int
    use_tls: bool
    username: str
    password: str
    default_sender: str


def _get_bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_mail_configuration_error():
    missing_keys = [name for name in REQUIRED_MAIL_ENV if not os.getenv(name)]
    if missing_keys:
        return "Konfigurasi email belum lengkap: " + ", ".join(missing_keys)

    try:
        int(os.getenv("MAIL_PORT", ""))
    except ValueError:
        return "MAIL_PORT harus berupa angka."

    return None


def is_mail_configured():
    return get_mail_configuration_error() is None


def _load_mail_config():
    configuration_error = get_mail_configuration_error()
    if configuration_error:
        raise MailConfigurationError(configuration_error)

    return MailConfig(
        server=os.getenv("MAIL_SERVER", "").strip(),
        port=int(os.getenv("MAIL_PORT", "").strip()),
        use_tls=_get_bool_env("MAIL_USE_TLS", default=True),
        username=os.getenv("MAIL_USERNAME", "").strip(),
        password=os.getenv("MAIL_PASSWORD", ""),
        default_sender=os.getenv("MAIL_DEFAULT_SENDER", "").strip(),
    )


def _format_duration(seconds):
    if seconds == 3600:
        return "1 jam"
    if seconds % 3600 == 0:
        return f"{seconds // 3600} jam"
    if seconds % 60 == 0:
        return f"{seconds // 60} menit"
    return f"{seconds} detik"


def send_password_reset_email(recipient_email, recipient_name, reset_url, max_age_seconds):
    config = _load_mail_config()
    greeting_name = (recipient_name or "pengguna Pathora").strip()
    duration = _format_duration(max_age_seconds)

    message = EmailMessage()
    message["Subject"] = "Reset Password Pathora"
    message["From"] = config.default_sender
    message["To"] = recipient_email
    message.set_content(
        "\n".join(
            [
                f"Halo {greeting_name},",
                "",
                "Kami menerima permintaan reset password untuk akun Pathora Anda.",
                "Klik link berikut untuk membuat password baru:",
                reset_url,
                "",
                f"Link ini berlaku selama {duration}.",
                "Abaikan email ini jika Anda tidak meminta reset password.",
                "",
                "Salam,",
                "Tim Pathora",
            ]
        )
    )

    with smtplib.SMTP(config.server, config.port, timeout=10) as smtp:
        if config.use_tls:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(config.username, config.password)
        smtp.send_message(message)
