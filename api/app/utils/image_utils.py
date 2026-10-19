"""
Image decoding, format validation, and safety utilities for multimodal tools.
"""

import io
import re
import base64
import binascii
import logging
from typing import Optional, Union
from PIL import Image

logger = logging.getLogger("project_atlas.utils.image")


def validate_image_bytes(image_bytes: Optional[Union[bytes, bytearray]]) -> bool:
    """
    Verifies that the provided byte stream corresponds to a valid, readable image format.
    Catches corrupt headers, truncated streams, empty buffers, and non-image data.
    """
    if not image_bytes or not isinstance(image_bytes, (bytes, bytearray)):
        return False
    if len(image_bytes) < 8:  # Minimum header size for formats like PNG/JPEG
        return False

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
        return True
    except (Image.DecompressionBombError, OSError, ValueError) as exc:
        logger.debug("validate_image_bytes_failed error=%s", exc)
        return False


def decode_base64_image(b64_string: Optional[str]) -> Optional[bytes]:
    """
    Safely validates and decodes a base64 string into raw image bytes.
    Handles data URI prefixes (e.g. 'data:image/png;base64,...'), padding issues,
    corrupted characters, empty strings, and verifies valid image headers.
    Returns bytes if valid image, None otherwise.
    """
    if not b64_string or not isinstance(b64_string, str):
        logger.warning("decode_base64_image_failed: input is empty or not a string")
        return None

    cleaned = b64_string.strip()
    if not cleaned:
        logger.warning("decode_base64_image_failed: input is empty or whitespace")
        return None

    # Strip data URI prefix if present (e.g., 'data:image/png;base64,...')
    if cleaned.startswith("data:"):
        cleaned = re.sub(r"^data:[^;]+;base64,", "", cleaned).strip()

    # Normalize padding if missing
    missing_padding = len(cleaned) % 4
    if missing_padding:
        cleaned += "=" * (4 - missing_padding)

    try:
        raw_bytes = base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError) as exc:
        logger.warning("decode_base64_image_failed: malformed or corrupt base64 string error=%s", exc)
        return None

    if not validate_image_bytes(raw_bytes):
        logger.warning("decode_base64_image_failed: decoded bytes are not a valid image format")
        return None

    return raw_bytes
