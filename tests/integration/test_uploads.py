from httpx import AsyncClient
import pytest
import io
from pathlib import Path
from source.main import app  
from source.dependencies.mediafile import get_mediafile_service
from source.services.mediafile import MediaFileService
from source.repositories.mediafile import MediaFileRepository
from source.services.storage.localStorage import LocalStorage
from source.dependencies.rate_limit import upload_limiter


@pytest.mark.asyncio(loop_scope="session")
class TestUploads:

    async def test_upload_file_local_storage(self, 
                              async_client: AsyncClient,
                              tmp_path: Path,
                              db_session,
                              authenticated_user,
                              test_app):
        
        # override storage path
        def override_get_mediafile_service():
            storage = LocalStorage(tmp_path) 
            return MediaFileService(MediaFileRepository(db_session), storage)
        
        test_app.dependency_overrides[get_mediafile_service] = override_get_mediafile_service

        # test file
        file_data = b"Hello, world! This is a test file."
        file_name = "test_image.png"
        
        # request
        response = await async_client.post(
            "/upload/one-file",
            files={"file": (file_name, io.BytesIO(file_data), "image/png")},
            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"}
        )

        # check response
        assert response.status_code == 200
        
        # check if file in storage
        uploaded_files = list(tmp_path.glob("*_test_image.png"))
        assert len(uploaded_files) == 1 # не проходит этот тест. здесь 0 а должно быть 1
        assert uploaded_files[0].read_bytes() == file_data

        # clear override
        app.dependency_overrides.clear()
        
        