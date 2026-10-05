from typing import Optional

from fastapi import HTTPException, UploadFile, status

MAX_PHOTO_BYTES = 5 * 1024 * 1024
# Detect the real image type from the file signature, so a script or HTML file cannot be stored as a "photo".
PHOTO_SIGNATURES = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
}
PHOTO_MEDIA_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def detect_photo_extension(content: bytes) -> Optional[str]:
    for signature, ext in PHOTO_SIGNATURES.items():
        if content.startswith(signature):
            return ext
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


def read_validated_photo(file: UploadFile) -> tuple[bytes, str]:
    """Read an uploaded photo and return (content, extension); JPEG, PNG or WebP up to 5 MB."""
    content = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Photo must be at most 5 MB")
    ext = detect_photo_extension(content)
    if not ext:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image. Upload a JPEG, PNG or WebP photo")
    return content, ext
