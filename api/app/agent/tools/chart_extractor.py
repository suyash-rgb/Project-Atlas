"""
Multimodal Chart Extractor & Visual Ground Truth Summarizer.

Uses PyMuPDF to extract embedded vector/raster charts from PDF market reports
and passes them to Gemini 3.5 Flash Lite vision model to convert graphics,
donut slices, and trajectory lines into structured, verifiable Markdown tables.
"""

import io
import os
import re
import base64
import binascii
import logging
from typing import Dict, Any, List, Optional, Union
from PIL import Image, UnidentifiedImageError
import pymupdf
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("project_atlas.chart_extractor")

CHART_CACHE_DIR = "data/chart_summaries"


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
    except (UnidentifiedImageError, OSError, Exception) as exc:
        logger.debug("validate_image_bytes_failed error=%s", exc)
        return False


def get_gemini_client():
    """Initialize Google GenAI client if API key is present."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("gemini_api_key_missing multimodal chart vision extraction skipped")
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as exc:
        logger.warning("google_genai_client_init_failed error=%s", exc)
        return None


def summarize_chart_image(
    image_input: Any,
    report_id: str,
    page_num: int,
    report_title: str,
    client: Optional[Any] = None,
) -> str:
    """
    Summarizes a chart image (accepts PIL Image, raw bytes, or base64 string).
    Returns formatted Markdown table and takeaways, or fallback text on error/client unavailability.
    """
    # Resolve raw image
    pil_img: Optional[Image.Image] = None

    if isinstance(image_input, Image.Image):
        pil_img = image_input
    elif isinstance(image_input, (bytes, bytearray)):
        if not validate_image_bytes(image_input):
            logger.warning("summarize_chart_image_failed: invalid image bytes")
            return ""
        pil_img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, str):
        decoded = decode_base64_image(image_input)
        if not decoded:
            logger.warning("summarize_chart_image_failed: base64 decoding returned no valid image")
            return ""
        pil_img = Image.open(io.BytesIO(decoded))
    else:
        logger.warning("summarize_chart_image_failed: unsupported image input type=%s", type(image_input))
        return ""

    if client is None:
        client = get_gemini_client()

    if client is None:
        logger.info("gemini_client_none: returning structured fallback representation")
        return f"Visual Market Chart on Page {page_num} of {report_title} (Report {report_id})."

    try:
        prompt = (
            f"You are an expert market research data extractor analyzing Report {report_id}: '{report_title}' (Page {page_num}).\n"
            f"Extract all visual data points, categories, percentages, numbers, timeline years, and trends from this chart.\n"
            f"Format the output strictly as:\n"
            f"### Chart: [Descriptive Chart Title]\n"
            f"[Structured Markdown Table with all exact figures]\n"
            f"**Key Visual Takeaways:**\n"
            f"- Bullet points of key findings"
        )
        resp = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=[prompt, pil_img]
        )
        summary = resp.text.strip() if (resp and resp.text) else ""
        if not summary:
            return f"Visual Market Chart on Page {page_num} of {report_title} (Report {report_id})."
        return summary
    except Exception as exc:
        logger.warning("gemini_vision_call_failed report_id=%s page=%s error=%s", report_id, page_num, exc)
        return f"Visual Market Chart on Page {page_num} of {report_title} (Report {report_id}) [Vision processing error]."


def extract_and_summarize_charts_from_pdf(
    pdf_path: str,
    report_id: str,
    report_title: str,
    min_size_bytes: int = 15000,
) -> List[Dict[str, Any]]:
    """
    Extracts embedded charts from a report PDF, validates image integrity,
    sends them to Gemini 3.5 Flash Lite for structured visual summarization,
    and returns enriched chart documents. Gracefully handles 0 charts, corrupted images,
    non-existent PDFs, and API errors.
    """
    if not pdf_path or not isinstance(pdf_path, str) or not os.path.exists(pdf_path):
        logger.warning("extract_charts_aborted: pdf path does not exist path=%s", pdf_path)
        return []

    os.makedirs(CHART_CACHE_DIR, exist_ok=True)
    client = get_gemini_client()
    chart_chunks: List[Dict[str, Any]] = []

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        logger.error("pymupdf_open_failed path=%s error=%s", pdf_path, exc)
        return []

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            actual_page_num = page_num + 1

            try:
                images = page.get_images(full=True)
            except Exception as exc:
                logger.warning("get_images_failed page=%s error=%s", actual_page_num, exc)
                continue

            for img_idx, img in enumerate(images, start=1):
                xref = img[0]
                try:
                    base_img = doc.extract_image(xref)
                    img_bytes = base_img.get("image")
                    
                    if not img_bytes or len(img_bytes) < min_size_bytes:
                        continue  # Ignore tiny decorative icons/logos

                    # Validate byte integrity before passing to cache or Vision LLM
                    if not validate_image_bytes(img_bytes):
                        logger.warning("corrupted_image_skipped xref=%s page=%s", xref, actual_page_num)
                        continue

                    cache_key = f"{report_id}_p{actual_page_num}_img{img_idx}.md"
                    cache_path = os.path.join(CHART_CACHE_DIR, cache_key)

                    # Use cached summary if available to save tokens/time
                    if os.path.exists(cache_path):
                        with open(cache_path, "r", encoding="utf-8") as f:
                            summary_text = f.read().strip()
                    else:
                        summary_text = summarize_chart_image(
                            image_input=img_bytes,
                            report_id=report_id,
                            page_num=actual_page_num,
                            report_title=report_title,
                            client=client,
                        )
                        if summary_text and not summary_text.endswith("[Vision processing error]."):
                            try:
                                with open(cache_path, "w", encoding="utf-8") as f:
                                    f.write(summary_text)
                            except Exception as write_err:
                                logger.warning("cache_write_failed path=%s error=%s", cache_path, write_err)

                    if summary_text:
                        chart_chunks.append({
                            "report_id": report_id,
                            "page": actual_page_num,
                            "text": f"VISUAL EVIDENCE [Chart on Page {actual_page_num}]:\n{summary_text}",
                            "title": report_title,
                            "img_idx": img_idx,
                        })
                        logger.info("chart_extracted report_id=%s page=%s img_idx=%s bytes=%s", report_id, actual_page_num, img_idx, len(img_bytes))
                except Exception as e:
                    logger.warning("chart_extraction_failed report_id=%s page=%s img_idx=%s error=%s", report_id, actual_page_num, img_idx, e)
    finally:
        try:
            doc.close()
        except Exception:
            pass

    return chart_chunks
