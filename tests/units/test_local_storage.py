import pytest
import io

from pathlib import Path
from fastapi import UploadFile

from source.services.storage.localStorage import LocalStorage
from source.core.exceptions import FileWritingException
from source.core.types import FileTypeEnum


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path)


def make_upload_file(
    filename="image.jpg",
    content=b"image data",
    content_type="image/jpeg",
):
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers={"content-type": content_type},
    )

class TestLocalStorage:

    def test_save_success(self, storage):
        
        upload = make_upload_file()

        saved = storage.save(upload)

        saved_path = storage.upload_dir / saved.filename

        assert saved_path.exists()
        assert saved_path.read_bytes() == b"image data"

        assert saved.mime_type == "image/jpeg"
        assert saved.file_type == FileTypeEnum.IMAGE
        assert saved.size == len(b"image data")
        assert saved.filename.endswith("_image.jpg")


    def test_save_without_content_type(self, storage):
        upload = UploadFile(
            filename="test.txt",
            file=io.BytesIO(b"data"),
        )

        with pytest.raises(FileWritingException, match="Content type is missing"):
            storage.save(upload)


    def test_save_os_error(self, storage, monkeypatch):
        upload = make_upload_file()

        def fake_open(*args, **kwargs):
            raise OSError("disk error")

        monkeypatch.setattr("builtins.open", fake_open)

        with pytest.raises(FileWritingException, match="Failed to save file"):
            storage.save(upload)

        assert list(storage.upload_dir.iterdir()) == []


    def test_delete_existing_file(self, storage):
        file_path = storage.upload_dir / "test.txt"
        file_path.write_text("hello")

        storage.delete("test.txt")

        assert not file_path.exists()


    def test_delete_non_existing_file(self, storage):
        storage.delete("missing.txt")


    def test_delete_os_error(self, storage, monkeypatch):
        file_path = storage.upload_dir / "test.txt"
        file_path.write_text("hello")

        def fake_unlink():
            raise OSError()

        monkeypatch.setattr(Path, "unlink", lambda self: fake_unlink())

        # метод не должен пробрасывать исключение
        storage.delete("test.txt")

        assert file_path.exists()
    
