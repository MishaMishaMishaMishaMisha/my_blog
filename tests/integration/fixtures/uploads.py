import mimetypes
import pytest
import pytest_asyncio

from pathlib import Path
from fastapi import UploadFile

from source.models.attachment_media import AttachmentMediaModel
from source.core.types import FileTypeEnum


@pytest.fixture
def media_file(test_media_dir):

    def factory(filename: str = "image.jpg") -> Path:
        return test_media_dir / filename

    return factory


@pytest.fixture
def upload_file(media_file):

    def factory(filename="image.jpg"):

        path = media_file(filename)

        return UploadFile(
            filename=path.name,
            file=path.open("rb"),
        )

    return factory


@pytest.fixture
def attachment_factory():

    def factory(
        *,
        user_id,
        filename: str = "image.jpg",
        **kwargs,
    ):

        mime_type = mimetypes.guess_type(filename)[0]
        if not mime_type:
            mime_type = "image/png"

        file_type = (
            FileTypeEnum.IMAGE
            if mime_type.startswith("image/")
            else FileTypeEnum.VIDEO
        )

        defaults = {
            "user_id": user_id,
            "filename": filename,
            "file_type": file_type,
            "mime_type": mime_type,
            "size": 1024,
            "is_temporary": True,
            "post_id": None,
            "comment_id": None,
        }

        defaults.update(kwargs)

        return AttachmentMediaModel(**defaults)

    return factory



@pytest_asyncio.fixture
async def attachments_factory(
    db_session,
    attachment_factory,
):

    async def factory(
        *,
        user,
        count: int = 1,
        filename: str = "image.jpg",
        **kwargs,
    ):

        attachments = [
            attachment_factory(
                user_id=user.id,
                filename=filename,
                **kwargs,
            )
            for _ in range(count)
        ]

        db_session.add_all(attachments)

        await db_session.commit()

        for attachment in attachments:
            await db_session.refresh(attachment)

        return attachments

    return factory
