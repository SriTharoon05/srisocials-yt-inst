"""Private Supabase objects in production; local files for development only."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
import httpx
from fastapi import HTTPException
from app.config import settings


def headers():
    return {"Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key}


def endpoint(key, action="object"):
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/{action}/{quote(settings.supabase_storage_bucket, safe='')}/{quote(key, safe='')}"


def save(path: Path):
    if not settings.supabase_url:
        return str(path)
    with path.open("rb") as source:
        response = httpx.post(endpoint(path.name), headers={**headers(), "Content-Type": "video/mp4"},
                              content=source, timeout=120)
    if response.is_error:
        raise HTTPException(502, "Private storage upload failed; check bucket configuration/quota")
    path.unlink(missing_ok=True)
    return "supabase:" + path.name


def signed_url(path, seconds=3600):
    if not path.startswith("supabase:"):
        raise HTTPException(400, "Instagram requires Supabase private storage with an HTTPS URL")
    response = httpx.post(endpoint(path[9:], "object/sign"), headers=headers(), json={"expiresIn": seconds}, timeout=30)
    if response.is_error:
        raise HTTPException(502, "Cannot create temporary video URL")
    url = response.json()["signedURL"]
    return settings.supabase_url.rstrip("/") + "/storage/v1" + url


@contextmanager
def local_file(path):
    if not path.startswith("supabase:"):
        if not Path(path).is_file():
            raise HTTPException(404, "Video file is missing")
        yield path
        return
    with TemporaryDirectory() as directory:
        target = Path(directory) / "video.mp4"
        with httpx.stream("GET", signed_url(path), timeout=120) as response:
            response.raise_for_status()
            with target.open("wb") as out:
                for chunk in response.iter_bytes(1024 * 1024):
                    out.write(chunk)
        yield str(target)


def delete(path):
    if path.startswith("supabase:"):
        response = httpx.request(
            "DELETE", f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_storage_bucket}",
            headers=headers(), json={"prefixes": [path[9:]]}, timeout=30)
        if response.is_error:
            raise HTTPException(502, "Storage deletion failed; retry")
    else:
        Path(path).unlink(missing_ok=True)
