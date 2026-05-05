from pathlib import Path

from prady_models.download import DownloadSpec, Downloader


class FakeResp:
    def __init__(self, status_code=200, json_payload=None, content=b"hello"):
        self.status_code = status_code
        self._json = json_payload or {}
        self.raw = None
        self._content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def __enter__(self):
        import io

        self.raw = io.BytesIO(self._content)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self):
        self._meta_payload = {
            "siblings": [
                {
                    "rfilename": "model.gguf",
                    "lfs": {
                        "oid": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
                    },
                }
            ]
        }

    def get(self, url, timeout=20, stream=False):
        if "api/models" in url:
            return FakeResp(status_code=200, json_payload=self._meta_payload)
        return FakeResp(status_code=200, content=b"hello")

    def head(self, url, allow_redirects=True, timeout=20):
        return FakeResp(status_code=200)


def test_resolve_hf_and_download_sha(tmp_path: Path):
    downloader = Downloader(session=FakeSession())
    spec = downloader.resolve_hf("org/repo", "model.gguf")

    path, sha = downloader.download_file(spec, tmp_path)
    assert path.exists()
    assert sha == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_resolve_github(tmp_path: Path):
    downloader = Downloader(session=FakeSession())
    spec = downloader.resolve_github("https://github.com/org/repo/releases/download/v1/model.gguf")
    assert isinstance(spec, DownloadSpec)
    assert spec.file_name == "model.gguf"
