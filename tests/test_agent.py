"""
Tests for the Invoice Processor Agent.

Run locally:
    pytest tests/ -v

Or with a running server:
    BASE_URL=http://localhost:8000 pytest tests/ -v
"""

import io
import json
import os
import sys

import pytest

# Allow imports from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Unit tests (no API key needed) ─────────────────────────────────────────────

class TestUtils:
    def test_validate_file_allowed_extension(self):
        from utils import validate_file
        validate_file("invoice.pdf", 1024)  # Should not raise

    def test_validate_file_disallowed_extension(self):
        from utils import validate_file
        with pytest.raises(ValueError, match="not supported"):
            validate_file("invoice.docx", 1024)

    def test_validate_file_too_large(self):
        from utils import validate_file
        with pytest.raises(ValueError, match="too large"):
            validate_file("invoice.pdf", 25 * 1024 * 1024)  # 25 MB > 20 MB limit

    def test_image_to_base64_returns_dict(self):
        from utils import image_to_base64
        result = image_to_base64(b"fake_image_bytes", "image/png")
        assert result["type"] == "base64"
        assert result["media_type"] == "image/png"
        assert isinstance(result["data"], str)

    def test_get_file_extension(self):
        from utils import get_file_extension
        assert get_file_extension("invoice.PDF") == "pdf"
        assert get_file_extension("file.jpg") == "jpg"
        assert get_file_extension("noextension") == ""


class TestModels:
    def test_invoice_data_defaults(self):
        from models import InvoiceData
        data = InvoiceData()
        assert data.line_items == []
        assert data.total_amount is None

    def test_line_item(self):
        from models import LineItem
        item = LineItem(description="Service A", quantity=2, unit_price=100.0, total=200.0)
        assert item.total == 200.0

    def test_invoice_response(self):
        from models import InvoiceResponse, InvoiceData
        resp = InvoiceResponse(
            success=True,
            invoice_id="test-123",
            filename="invoice.pdf",
            data=InvoiceData(total_amount=500.0),
            processing_time_ms=300,
        )
        assert resp.success is True
        assert resp.data.total_amount == 500.0


class TestAgentParsing:
    """Test the JSON parsing logic without hitting the API."""

    def test_parse_clean_json(self):
        from agent import InvoiceProcessorAgent
        # Bypass __init__ API key check for unit test
        ag = object.__new__(InvoiceProcessorAgent)
        raw = '{"vendor_name": "Acme", "total_amount": 100.0, "line_items": []}'
        result = ag._parse_json(raw)
        assert result["vendor_name"] == "Acme"

    def test_parse_json_with_code_fence(self):
        from agent import InvoiceProcessorAgent
        ag = object.__new__(InvoiceProcessorAgent)
        raw = "```json\n{\"total_amount\": 200}\n```"
        result = ag._parse_json(raw)
        assert result["total_amount"] == 200

    def test_to_float(self):
        from agent import InvoiceProcessorAgent
        assert InvoiceProcessorAgent._to_float("123.45") == 123.45
        assert InvoiceProcessorAgent._to_float(None) is None
        assert InvoiceProcessorAgent._to_float("bad") is None

    def test_dict_to_invoice_data(self):
        from agent import InvoiceProcessorAgent
        ag = object.__new__(InvoiceProcessorAgent)
        data = {
            "vendor_name": "Acme Corp",
            "total_amount": "1500.00",
            "currency": "USD",
            "line_items": [
                {"description": "Dev work", "quantity": 10, "unit_price": 150, "total": 1500}
            ],
        }
        invoice = ag._dict_to_invoice_data(data)
        assert invoice.vendor_name == "Acme Corp"
        assert invoice.total_amount == 1500.0
        assert len(invoice.line_items) == 1
        assert invoice.line_items[0].description == "Dev work"


# ── Integration tests (requires running server) ──────────────────────────────

BASE_URL = os.getenv("BASE_URL", "")


@pytest.mark.skipif(not BASE_URL, reason="Set BASE_URL env var to run integration tests")
class TestAPI:
    def test_health(self):
        import urllib.request
        with urllib.request.urlopen(f"{BASE_URL}/health") as resp:
            data = json.loads(resp.read())
        assert data["status"] == "ok"

    def test_process_sample_invoice(self):
        """Requires tests/sample_invoice.pdf — run create_sample_invoice.py first."""
        import urllib.request
        import urllib.parse

        sample_path = os.path.join(os.path.dirname(__file__), "sample_invoice.pdf")
        if not os.path.exists(sample_path):
            pytest.skip("sample_invoice.pdf not found — run create_sample_invoice.py first")

        with open(sample_path, "rb") as f:
            file_data = f.read()

        boundary = "----TestBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="sample_invoice.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{BASE_URL}/process",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())

        assert result["success"] is True
        assert result["data"]["vendor_name"] is not None
        assert result["data"]["total_amount"] is not None
        print("\n📄 Extracted Invoice Data:")
        print(json.dumps(result["data"], indent=2))
