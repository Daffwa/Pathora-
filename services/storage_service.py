import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_CHAT_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_CHAT_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}
CHAT_IMAGE_MAX_BYTES = 5 * 1024 * 1024


def secure_upload_filename(filename: str | None) -> str:
    """Return a filesystem-safe upload filename."""
    return secure_filename(filename or "")


def allowed_file(filename: str | None, allowed_extensions: Iterable[str]) -> bool:
    """Check whether a filename has an allowed extension."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in {
        allowed_extension.lower() for allowed_extension in allowed_extensions
    }


def is_allowed_file(filename: str | None) -> bool:
    """Check document upload extensions."""
    return allowed_file(filename, ALLOWED_EXTENSIONS)


def is_allowed_image_file(filename: str | None) -> bool:
    """Check profile avatar image extensions."""
    return allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS)


def validate_document_upload(uploaded_file: FileStorage | None) -> bool:
    """Validate a document upload based on its filename."""
    return bool(
        uploaded_file
        and uploaded_file.filename
        and is_allowed_file(uploaded_file.filename)
    )


def validate_image_upload(uploaded_file: FileStorage | None) -> bool:
    """Validate an avatar upload based on its filename."""
    return bool(
        uploaded_file
        and uploaded_file.filename
        and is_allowed_image_file(uploaded_file.filename)
    )


def has_allowed_chat_image_signature(
    uploaded_file: FileStorage | None,
    extension: str,
) -> bool:
    """Validate chat image file signatures without consuming the upload stream."""
    if uploaded_file is None:
        return False

    try:
        current_position = uploaded_file.stream.tell()
        uploaded_file.stream.seek(0)
        header = uploaded_file.stream.read(16)
        uploaded_file.stream.seek(current_position)
    except (OSError, AttributeError):
        return False

    if extension == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == "gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if extension == "webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"

    return False


def is_allowed_chat_image_file(uploaded_file: FileStorage | None) -> bool:
    """Validate chat image extension, MIME type, and binary signature."""
    if uploaded_file is None or not uploaded_file.filename:
        return False

    if "." not in uploaded_file.filename:
        return False

    extension = uploaded_file.filename.rsplit(".", 1)[1].lower()
    return (
        extension in ALLOWED_CHAT_IMAGE_EXTENSIONS
        and uploaded_file.mimetype in ALLOWED_CHAT_IMAGE_MIME_TYPES
        and has_allowed_chat_image_signature(uploaded_file, extension)
    )


def validate_chat_image_upload(
    uploaded_file: FileStorage | None,
    max_bytes: int = CHAT_IMAGE_MAX_BYTES,
) -> tuple[bool, str]:
    """Validate a chat image upload and return an error message when invalid."""
    if uploaded_file is None or not uploaded_file.filename:
        return False, "Pesan atau gambar wajib diisi."
    if not is_allowed_chat_image_file(uploaded_file):
        return False, "Hanya file gambar yang dapat dikirim."
    if get_uploaded_file_size(uploaded_file) > max_bytes:
        return False, "Ukuran gambar maksimal 5 MB."
    return True, ""


def get_uploaded_file_size(uploaded_file: FileStorage | None) -> int:
    """Return an uploaded file size while preserving the stream position."""
    if uploaded_file is None:
        return 0

    try:
        current_position = uploaded_file.stream.tell()
        uploaded_file.stream.seek(0, os.SEEK_END)
        size = uploaded_file.stream.tell()
        uploaded_file.stream.seek(current_position)
        return size
    except (OSError, AttributeError):
        return uploaded_file.content_length or 0


def _extension_from_filename(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def generate_unique_filename(
    user_id: int | str,
    original_filename: str | None,
    prefix: str,
    timestamp: datetime | None = None,
) -> str:
    """Generate a unique upload filename using user id, timestamp, and UUID."""
    safe_name = secure_upload_filename(original_filename)
    extension = _extension_from_filename(safe_name) or _extension_from_filename(
        original_filename
    )
    created_at = timestamp or datetime.now(timezone.utc)
    timestamp_part = created_at.strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{user_id}_{timestamp_part}_{uuid.uuid4().hex}.{extension}"


def make_chat_attachment_filename(
    user_id: int | str,
    original_filename: str | None,
) -> str:
    """Generate the stored filename for a chat image attachment."""
    return generate_unique_filename(user_id, original_filename, "chat")


def make_avatar_filename(user_id: int | str, original_filename: str | None) -> str:
    """Generate the stored filename for a profile avatar."""
    extension = _extension_from_filename(original_filename)
    return f"user_{user_id}_avatar.{extension}"


def make_document_filename(
    user_id: int | str,
    doc_type: str,
    original_filename: str | None,
) -> str:
    """Generate the stored filename for a user document."""
    extension = _extension_from_filename(original_filename)
    safe_doc_type = secure_upload_filename(doc_type.replace("/", "_"))
    return f"user_{user_id}_{safe_doc_type}.{extension}"


def _safe_child_path(base_folder: str | Path, file_name: str | None) -> Path | None:
    if not file_name:
        return None

    base_path = Path(base_folder).resolve()
    target_path = (base_path / file_name).resolve()
    if target_path == base_path or base_path not in target_path.parents:
        return None
    return target_path


def save_uploaded_file(
    uploaded_file: FileStorage,
    upload_folder: str | Path,
    file_name: str,
) -> str:
    """Save an uploaded file into a configured upload folder."""
    target_path = _safe_child_path(upload_folder, file_name)
    if target_path is None:
        raise ValueError("Invalid upload filename.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    uploaded_file.save(target_path)
    return file_name


def delete_file_if_exists(base_folder: str | Path, file_name: str | None) -> bool:
    """Delete a stored upload file when it exists inside the base folder."""
    target_path = _safe_child_path(base_folder, file_name)
    if target_path is None or not target_path.exists():
        return False

    try:
        target_path.unlink()
        return True
    except OSError:
        return False


def is_safe_stored_filename(filename: str | None) -> bool:
    """Check whether a stored upload filename is already secure."""
    safe_filename = secure_upload_filename(filename)
    return bool(safe_filename and safe_filename == filename)
