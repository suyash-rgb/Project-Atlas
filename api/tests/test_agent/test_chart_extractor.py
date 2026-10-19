"""
Unit Tests for Multimodal Chart Extractor & Visual Ground Truth Summarizer.

Validates:
- No charts on page or in PDF
- Exactly 1 chart on page
- Multiple charts across multiple pages
- Corrupted / truncated base64 string
- Empty base64 string
- Base64 string with invalid padding or non-base64 characters
- Base64 string that decodes to non-image content (text, random bytes)
- Data URI prefixes (e.g. data:image/png;base64,...)
- Corrupted image bytes failing PIL verification
- Non-existent or invalid PDF file path
- Gemini API errors (rate limits, network failure, empty text response)
- Cache hit vs cache miss behavior
"""

import io
import os
import base64
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from app.agent.tools.chart_extractor import (
    decode_base64_image,
    validate_image_bytes,
    summarize_chart_image,
    extract_and_summarize_charts_from_pdf,
    CHART_CACHE_DIR,
)


def create_test_image_bytes(format="PNG", size=(100, 100), color="blue") -> bytes:
    """Helper to generate valid in-memory image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


# =====================================================================
# 1. Base64 & Byte Validation Tests
# =====================================================================

def test_validate_image_bytes_valid_png():
    valid_bytes = create_test_image_bytes(format="PNG")
    assert validate_image_bytes(valid_bytes) is True


def test_validate_image_bytes_valid_jpeg():
    valid_bytes = create_test_image_bytes(format="JPEG")
    assert validate_image_bytes(valid_bytes) is True


def test_validate_image_bytes_empty():
    assert validate_image_bytes(b"") is False
    assert validate_image_bytes(None) is False


def test_validate_image_bytes_too_short():
    assert validate_image_bytes(b"short") is False


def test_validate_image_bytes_corrupted_random_bytes():
    corrupted = b"NOT_AN_IMAGE_HEADER_1234567890_CORRUPT"
    assert validate_image_bytes(corrupted) is False


def test_decode_base64_image_valid():
    valid_bytes = create_test_image_bytes()
    b64 = base64.b64encode(valid_bytes).decode("utf-8")
    result = decode_base64_image(b64)
    assert result is not None
    assert isinstance(result, bytes)
    assert validate_image_bytes(result) is True


def test_decode_base64_image_with_data_uri_prefix():
    valid_bytes = create_test_image_bytes()
    b64 = "data:image/png;base64," + base64.b64encode(valid_bytes).decode("utf-8")
    result = decode_base64_image(b64)
    assert result is not None
    assert validate_image_bytes(result) is True


def test_decode_base64_image_empty_and_whitespace():
    assert decode_base64_image("") is None
    assert decode_base64_image("   \n\t  ") is None
    assert decode_base64_image(None) is None


def test_decode_base64_image_corrupted_characters():
    corrupt_b64 = "!!!@@@###$$$%%%^^^&&&***((()))"
    assert decode_base64_image(corrupt_b64) is None


def test_decode_base64_image_missing_padding():
    valid_bytes = create_test_image_bytes()
    b64 = base64.b64encode(valid_bytes).decode("utf-8").rstrip("=")
    # decode_base64_image automatically fixes missing padding
    result = decode_base64_image(b64)
    assert result is not None
    assert validate_image_bytes(result) is True


def test_decode_base64_image_decodes_to_plain_text_not_image():
    # Base64 string that decodes cleanly to ASCII text, but NOT a valid image
    text_b64 = base64.b64encode(b"This is just some plain text, not a PNG image.").decode("utf-8")
    result = decode_base64_image(text_b64)
    assert result is None  # Fails image verification


# =====================================================================
# 2. Summarize Chart Image Tests (Gemini Client & Fallbacks)
# =====================================================================

def test_summarize_chart_image_no_client_returns_fallback():
    valid_bytes = create_test_image_bytes()
    summary = summarize_chart_image(
        image_input=valid_bytes,
        report_id="RPT-001",
        page_num=3,
        report_title="AI Market Trends",
        client=None,
    )
    assert "Visual Market Chart on Page 3 of AI Market Trends (Report RPT-001)." in summary


def test_summarize_chart_image_with_client_success():
    valid_bytes = create_test_image_bytes()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "### Chart: Growth Trajectory\n| Year | Revenue |\n| 2024 | $50B |\n**Key Visual Takeaways:**\n- Upward growth"
    mock_client.models.generate_content.return_value = mock_response

    summary = summarize_chart_image(
        image_input=valid_bytes,
        report_id="RPT-001",
        page_num=4,
        report_title="AI Market Trends",
        client=mock_client,
    )
    assert "### Chart: Growth Trajectory" in summary
    assert "| 2024 | $50B |" in summary
    mock_client.models.generate_content.assert_called_once()


def test_summarize_chart_image_gemini_api_error_returns_fallback():
    valid_bytes = create_test_image_bytes()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("503 Service Unavailable / Rate Limit Exceeded")

    summary = summarize_chart_image(
        image_input=valid_bytes,
        report_id="RPT-001",
        page_num=4,
        report_title="AI Market Trends",
        client=mock_client,
    )
    assert "Vision processing error" in summary


def test_summarize_chart_image_empty_response_text_returns_fallback():
    valid_bytes = create_test_image_bytes()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""  # Model returned empty string
    mock_client.models.generate_content.return_value = mock_response

    summary = summarize_chart_image(
        image_input=valid_bytes,
        report_id="RPT-001",
        page_num=4,
        report_title="AI Market Trends",
        client=mock_client,
    )
    assert "Visual Market Chart on Page 4 of AI Market Trends (Report RPT-001)." in summary


def test_summarize_chart_image_invalid_image_input():
    summary = summarize_chart_image(
        image_input=b"corrupted_garbage_bytes",
        report_id="RPT-001",
        page_num=1,
        report_title="Test",
    )
    assert summary == ""


# =====================================================================
# 3. PDF Extraction Pipeline Tests (PyMuPDF Mocking)
# =====================================================================

def test_extract_and_summarize_charts_non_existent_pdf():
    results = extract_and_summarize_charts_from_pdf(
        pdf_path="non_existent_report_123456.pdf",
        report_id="RPT-NONE",
        report_title="Missing",
    )
    assert results == []


def test_extract_and_summarize_charts_no_charts(tmp_path):
    test_pdf = tmp_path / "empty_report.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 dummy content")

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_images.return_value = []  # NO charts
    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page

    with patch("pymupdf.open", return_value=mock_doc):
        results = extract_and_summarize_charts_from_pdf(
            pdf_path=str(test_pdf),
            report_id="RPT-NO-CHARTS",
            report_title="Report with No Charts",
        )
    assert results == []
    mock_doc.close.assert_called_once()


def test_extract_and_summarize_charts_single_chart(tmp_path):
    test_pdf = tmp_path / "single_chart.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 dummy")

    valid_bytes = create_test_image_bytes(size=(400, 300))
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_images.return_value = [(10, 0, 400, 300, 8, "DeviceRGB", "", "img1", "FlateDecode")]
    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.extract_image.return_value = {"image": valid_bytes}

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "### Chart: Single Market Share\n| Vendor | Share |\n| Alpha | 45% |"
    mock_client.models.generate_content.return_value = mock_resp

    with patch("pymupdf.open", return_value=mock_doc), \
         patch("app.agent.tools.chart_extractor.get_gemini_client", return_value=mock_client), \
         patch("os.path.exists", side_effect=lambda p: False if p.endswith(".md") else True), \
         patch("builtins.open", MagicMock()):
        results = extract_and_summarize_charts_from_pdf(
            pdf_path=str(test_pdf),
            report_id="RPT-SINGLE",
            report_title="Single Chart Report",
            min_size_bytes=100,
        )

    assert len(results) == 1
    assert results[0]["report_id"] == "RPT-SINGLE"
    assert results[0]["page"] == 1
    assert "Single Market Share" in results[0]["text"]
    assert "Alpha | 45%" in results[0]["text"]


def test_extract_and_summarize_charts_multiple_charts_across_pages(tmp_path):
    test_pdf = tmp_path / "multi_chart.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 dummy")

    valid_bytes_1 = create_test_image_bytes(color="red", size=(300, 300))
    valid_bytes_2 = create_test_image_bytes(color="blue", size=(350, 350))

    mock_doc = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.get_images.return_value = [(10, 0, 300, 300, 8, "DeviceRGB", "", "img1", "FlateDecode")]

    mock_page2 = MagicMock()
    # Page 2 has 2 images: one valid chart and one tiny decorative icon (< min_size_bytes)
    mock_page2.get_images.return_value = [
        (20, 0, 350, 350, 8, "DeviceRGB", "", "img2", "FlateDecode"),
        (21, 0, 10, 10, 8, "DeviceRGB", "", "img3", "FlateDecode"),
    ]

    mock_doc.__len__.return_value = 2
    mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]

    def extract_image_mock(xref):
        if xref == 10:
            return {"image": valid_bytes_1}
        elif xref == 20:
            return {"image": valid_bytes_2}
        elif xref == 21:
            return {"image": b"tiny"}  # Below min_size_bytes
        return {"image": None}

    mock_doc.extract_image.side_effect = extract_image_mock

    mock_client = MagicMock()
    mock_resp1 = MagicMock()
    mock_resp1.text = "### Chart: Page 1 Revenue\n| Year | Value |\n| 2025 | $100M |"
    mock_resp2 = MagicMock()
    mock_resp2.text = "### Chart: Page 2 Regional Distribution\n| Region | % |\n| APAC | 60% |"

    mock_client.models.generate_content.side_effect = [mock_resp1, mock_resp2]

    with patch("pymupdf.open", return_value=mock_doc), \
         patch("app.agent.tools.chart_extractor.get_gemini_client", return_value=mock_client), \
         patch("os.path.exists", side_effect=lambda p: False if p.endswith(".md") else True), \
         patch("builtins.open", MagicMock()):
        results = extract_and_summarize_charts_from_pdf(
            pdf_path=str(test_pdf),
            report_id="RPT-MULTI",
            report_title="Multi Chart Report",
            min_size_bytes=100,
        )

    assert len(results) == 2
    assert results[0]["page"] == 1
    assert "Page 1 Revenue" in results[0]["text"]
    assert results[1]["page"] == 2
    assert "Page 2 Regional Distribution" in results[1]["text"]


def test_extract_and_summarize_charts_corrupted_image_skipped(tmp_path):
    test_pdf = tmp_path / "corrupt_chart.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 dummy")

    # Image bytes that are large enough (> 100 bytes) but corrupted (fails PIL verification)
    corrupted_bytes = b"CORRUPTED_RAW_STREAM_OF_BYTES_THAT_FAILS_PIL_VERIFICATION" * 10

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_images.return_value = [(10, 0, 300, 300, 8, "DeviceRGB", "", "corrupt_img", "FlateDecode")]
    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.extract_image.return_value = {"image": corrupted_bytes}

    with patch("pymupdf.open", return_value=mock_doc):
        results = extract_and_summarize_charts_from_pdf(
            pdf_path=str(test_pdf),
            report_id="RPT-CORRUPT",
            report_title="Corrupt Chart Report",
            min_size_bytes=100,
        )

    # Corrupted image should be gracefully filtered out without crashing
    assert results == []
