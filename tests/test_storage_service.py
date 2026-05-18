import os
import io
import tempfile
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage


@pytest.fixture(scope="function")
def temp_upload_dir():
    with tempfile.TemporaryDirectory(prefix="pytest_upload_") as tmp:
        yield Path(tmp)


@pytest.fixture(scope="function")
def storage_service(app_root):
    """Import storage_service fresh each test."""
    import importlib

    mod = importlib.import_module("services.storage_service")
    importlib.reload(mod)
    return mod


class TestDocumentUploadValidation:
    def test_accepts_pdf(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="resume.pdf")
        assert storage_service.validate_document_upload(f) is True

    def test_accepts_docx(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="letter.docx")
        assert storage_service.validate_document_upload(f) is True

    def test_accepts_png(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="scan.png")
        assert storage_service.validate_document_upload(f) is True

    def test_accepts_jpg(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="photo.jpg")
        assert storage_service.validate_document_upload(f) is True

    def test_accepts_jpeg(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="photo.jpeg")
        assert storage_service.validate_document_upload(f) is True

    def test_rejects_exe(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="virus.exe")
        assert storage_service.validate_document_upload(f) is False

    def test_rejects_zip(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="archive.zip")
        assert storage_service.validate_document_upload(f) is False

    def test_rejects_no_extension(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="Makefile")
        assert storage_service.validate_document_upload(f) is False

    def test_rejects_empty_filename(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="")
        assert storage_service.validate_document_upload(f) is False

    def test_rejects_none(self, storage_service):
        assert storage_service.validate_document_upload(None) is False


class TestImageUploadValidation:
    def test_accepts_png(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="avatar.png")
        assert storage_service.validate_image_upload(f) is True

    def test_accepts_jpg(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="avatar.jpg")
        assert storage_service.validate_image_upload(f) is True

    def test_rejects_gif(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="avatar.gif")
        assert storage_service.validate_image_upload(f) is False

    def test_rejects_webp(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="avatar.webp")
        assert storage_service.validate_image_upload(f) is False


class TestChatImageValidation:
    def test_rejects_non_image(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"not an image"), filename="note.txt")
        is_valid, _ = storage_service.validate_chat_image_upload(f)
        assert is_valid is False

    def test_rejects_exe(self, storage_service):
        f = FileStorage(stream=io.BytesIO(b"dummy"), filename="virus.exe")
        is_valid, _ = storage_service.validate_chat_image_upload(f)
        assert is_valid is False

    def test_accepts_real_png_signature(self, storage_service):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        f = FileStorage(
            stream=io.BytesIO(png_header),
            filename="chat.png",
            content_type="image/png",
        )
        is_valid, _ = storage_service.validate_chat_image_upload(f)
        assert is_valid is True

    def test_accepts_real_jpeg_signature(self, storage_service):
        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        f = FileStorage(
            stream=io.BytesIO(jpeg_header),
            filename="chat.jpg",
            content_type="image/jpeg",
        )
        is_valid, _ = storage_service.validate_chat_image_upload(f)
        assert is_valid is True

    def test_rejects_fake_png_wrong_signature(self, storage_service):
        fake_header = b"GIF89a" + b"\x00" * 20
        f = FileStorage(
            stream=io.BytesIO(fake_header),
            filename="fake.png",
            content_type="image/png",
        )
        is_valid, _ = storage_service.validate_chat_image_upload(f)
        assert is_valid is False

    def test_rejects_oversized(self, storage_service):
        data = b"\x89PNG\r\n\x1a\n" + b"A" * (6 * 1024 * 1024)
        f = FileStorage(
            stream=io.BytesIO(data),
            filename="large.png",
            content_type="image/png",
        )
        is_valid, _ = storage_service.validate_chat_image_upload(f)
        assert is_valid is False


class TestPathTraversalProtection:
    def test_save_rejects_traversal(self, storage_service, temp_upload_dir):
        f = FileStorage(stream=io.BytesIO(b"data"), filename="test.pdf")
        with pytest.raises(ValueError, match="Invalid upload filename"):
            storage_service.save_uploaded_file(f, str(temp_upload_dir), "../../etc/passwd")

    def test_delete_rejects_traversal(self, storage_service, temp_upload_dir):
        result = storage_service.delete_file_if_exists(
            str(temp_upload_dir), "../../etc/passwd"
        )
        assert result is False

    def test_delete_nonexistent_returns_false(self, storage_service, temp_upload_dir):
        result = storage_service.delete_file_if_exists(
            str(temp_upload_dir), "nonexistent.txt"
        )
        assert result is False

    def test_save_and_delete_roundtrip(self, storage_service, temp_upload_dir):
        f = FileStorage(stream=io.BytesIO(b"real data"), filename="test.pdf")
        storage_service.save_uploaded_file(f, str(temp_upload_dir), "mydoc.pdf")
        target = temp_upload_dir / "mydoc.pdf"
        assert target.exists()
        result = storage_service.delete_file_if_exists(str(temp_upload_dir), "mydoc.pdf")
        assert result is True
        assert not target.exists()


class TestSecureFilename:
    def test_secure_filename_basic(self, storage_service):
        result = storage_service.secure_upload_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_secure_filename_clean(self, storage_service):
        result = storage_service.secure_upload_filename("resume.pdf")
        assert result == "resume.pdf"

    def test_secure_filename_empty(self, storage_service):
        result = storage_service.secure_upload_filename("")
        assert result == ""

    def test_secure_filename_none(self, storage_service):
        result = storage_service.secure_upload_filename(None)
        assert result == ""


class TestSafeStoredFilename:
    def test_safe_filename_valid(self, storage_service):
        assert storage_service.is_safe_stored_filename("user_1_cv.pdf") is True

    def test_safe_filename_with_path(self, storage_service):
        assert storage_service.is_safe_stored_filename("../user_1_cv.pdf") is False


class TestUniqueFilenameGeneration:
    def test_make_document_filename(self, storage_service):
        result = storage_service.make_document_filename(1, "CV", "resume.pdf")
        assert result.startswith("user_1_CV.")
        assert result.endswith(".pdf")

    def test_make_avatar_filename(self, storage_service):
        result = storage_service.make_avatar_filename(42, "photo.jpg")
        assert result == "user_42_avatar.jpg"

    def test_make_chat_filename(self, storage_service):
        result = storage_service.make_chat_attachment_filename(7, "image.png")
        assert result.startswith("chat_7_")
        assert result.endswith(".png")
