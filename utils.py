import base64
import io
import os
from typing import List

import fitz  # PyMuPDF
from PIL import Image


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "tiff"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))


def validate_file(filename: str, file_size_bytes: int) -> None:
    """Raise ValueError if file type or size is not allowed."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '.{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValueError(
            f"File too large ({file_size_bytes / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {MAX_FILE_SIZE_MB} MB"
        )


def pdf_to_images(pdf_bytes: bytes, dpi: int = 150) -> List[bytes]:
    """Convert each page of a PDF to a PNG image (bytes)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def image_to_base64(image_bytes: bytes, media_type: str = "image/png") -> dict:
    """Return an Anthropic-compatible image source dict."""
    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")
    return {
        "type": "base64",
        "media_type": media_type,
        "data": encoded,
    }


def normalize_image(image_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """
    Normalize an uploaded image to PNG for consistent processing.
    Returns (png_bytes, media_type).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    if ext == "pdf":
        raise ValueError("Use pdf_to_images() for PDF files.")

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), "image/png"


def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
