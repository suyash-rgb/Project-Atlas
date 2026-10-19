"""
Multimodal Chart Extractor & Visual Ground Truth Summarizer.

Uses PyMuPDF to extract embedded raster charts from PDF market reports
and passes them to a configured Gemini vision model to convert graphics,
donut slices, and trajectory lines into structured, verifiable Markdown tables.
"""

import io
import os
import re
import base64
import binascii
import hashlib
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union
from PIL import Image
import pymupdf

from app.core.config import settings

logger = logging.getLogger("project_atlas.chart_extractor")

CHART_CACHE_DIR = settings.CHART_CACHE_DIR
CHART_PROMPT_VERSION = "1"


from app.utils.image_utils import decode_base64_image, validate_image_bytes


def get_gemini_client():
    """Initialize Google GenAI client if API key is present."""
    api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
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
    client: Any = "AUTO",
) -> str:
    """
    Summarizes a chart image (accepts PIL Image, raw bytes, or base64 string).
    Returns formatted Markdown table and takeaways, or fallback text on error/client unavailability.
    """
    # Copy loaded images so the request has a live image after its byte stream closes.
    pil_img: Optional[Image.Image] = None

    if isinstance(image_input, Image.Image):
        pil_img = image_input.copy()
    elif isinstance(image_input, (bytes, bytearray)):
        if not validate_image_bytes(image_input):
            logger.warning("summarize_chart_image_failed: invalid image bytes")
            return ""
        with Image.open(io.BytesIO(image_input)) as source:
            pil_img = source.copy()
    elif isinstance(image_input, str):
        decoded = decode_base64_image(image_input)
        if not decoded:
            logger.warning("summarize_chart_image_failed: base64 decoding returned no valid image")
            return ""
        with Image.open(io.BytesIO(decoded)) as source:
            pil_img = source.copy()
    else:
        logger.warning("summarize_chart_image_failed: unsupported image input type=%s", type(image_input))
        return ""

    if client == "AUTO":
        client = get_gemini_client()

    try:
        if not client:
            logger.info("gemini_client_none: returning structured fallback representation")
            return f"Visual Market Chart on Page {page_num} of {report_title} (Report {report_id})."

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
            model=settings.GEMINI_MODEL,
            contents=[prompt, pil_img]
        )
        summary = resp.text.strip() if (resp and resp.text) else ""
        if not summary:
            return f"Visual Market Chart on Page {page_num} of {report_title} (Report {report_id})."
        return summary
    except Exception as exc:
        logger.warning("gemini_vision_call_failed report_id=%s page=%s error=%s", report_id, page_num, exc)
        return f"Visual Market Chart on Page {page_num} of {report_title} (Report {report_id}) [Vision processing error]."
    finally:
        pil_img.close()


def extract_and_summarize_charts_from_pdf(
    pdf_path: str,
    report_id: str,
    report_title: str,
    min_size_bytes: int = 15000,
) -> List[Dict[str, Any]]:
    """
    Extracts embedded raster charts from a report PDF, validates image integrity,
    sends them to the configured Gemini vision model for structured summarization,
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

                    cache_fingerprint = hashlib.sha256(
                        b"\0".join(
                            (
                                report_id.encode("utf-8"),
                                str(actual_page_num).encode("ascii"),
                                str(img_idx).encode("ascii"),
                                report_title.encode("utf-8"),
                                settings.GEMINI_MODEL.encode("utf-8"),
                                CHART_PROMPT_VERSION.encode("ascii"),
                                img_bytes,
                            )
                        )
                    ).hexdigest()
                    cache_path = os.path.join(CHART_CACHE_DIR, f"{cache_fingerprint}.md")
                    legacy_cache_path = os.path.join(
                        CHART_CACHE_DIR,
                        f"{report_id}_p{actual_page_num}_img{img_idx}.md",
                    )

                    summary_text = ""
                    if os.path.exists(cache_path):
                        with open(cache_path, "r", encoding="utf-8") as f:
                            summary_text = f.read().strip()
                    elif (
                        re.fullmatch(r"[A-Za-z0-9_-]{1,64}", report_id)
                        and os.path.exists(legacy_cache_path)
                    ):
                        try:
                            os.replace(legacy_cache_path, cache_path)
                            with open(cache_path, "r", encoding="utf-8") as f:
                                summary_text = f.read().strip()
                        except OSError as cache_err:
                            logger.warning(
                                "legacy_chart_cache_migration_failed report_id=%s page=%s error=%s",
                                report_id,
                                actual_page_num,
                                cache_err,
                            )

                    if summary_text.startswith("Visual Market Chart on Page"):
                        summary_text = ""

                    if not summary_text:
                        summary_text = summarize_chart_image(
                            image_input=img_bytes,
                            report_id=report_id,
                            page_num=actual_page_num,
                            report_title=report_title,
                            client=client,
                        )
                        if (
                            summary_text
                            and not summary_text.startswith("Visual Market Chart on Page")
                            and not summary_text.endswith("[Vision processing error].")
                        ):
                            temporary_path = None
                            try:
                                with tempfile.NamedTemporaryFile(
                                    mode="w",
                                    encoding="utf-8",
                                    dir=CHART_CACHE_DIR,
                                    prefix=".chart-summary-",
                                    suffix=".tmp",
                                    delete=False,
                                ) as f:
                                    temporary_path = f.name
                                    f.write(summary_text)
                            except Exception as write_err:
                                logger.warning("cache_write_failed path=%s error=%s", cache_path, write_err)
                            else:
                                try:
                                    os.replace(temporary_path, cache_path)
                                except OSError as replace_err:
                                    logger.warning(
                                        "cache_write_failed path=%s error=%s",
                                        cache_path,
                                        replace_err,
                                    )
                            finally:
                                if temporary_path and os.path.exists(temporary_path):
                                    try:
                                        os.unlink(temporary_path)
                                    except OSError as cleanup_err:
                                        logger.warning(
                                            "cache_temp_cleanup_failed path=%s error=%s",
                                            temporary_path,
                                            cleanup_err,
                                        )

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
        doc.close()

    return chart_chunks
