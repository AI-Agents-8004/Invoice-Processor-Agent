import io
import json
import os
import re
from typing import List

from models import InvoiceData, LineItem
from utils import image_to_base64, normalize_image, pdf_to_images, get_file_extension


EXTRACTION_PROMPT = """You are an expert invoice data extraction agent. Carefully analyze the invoice image and extract every piece of information visible.

Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

Use this exact structure (set missing fields to null, not empty string):

{
    "vendor_name": "string",
    "vendor_address": "string",
    "vendor_email": "string",
    "vendor_phone": "string",
    "vendor_tax_id": "string",
    "client_name": "string",
    "client_address": "string",
    "client_email": "string",
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "purchase_order_number": "string",
    "currency": "3-letter ISO code e.g. USD",
    "line_items": [
        {
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number
        }
    ],
    "subtotal": number,
    "tax_rate": number,
    "tax_amount": number,
    "discount": number,
    "shipping": number,
    "total_amount": number,
    "payment_terms": "string",
    "payment_method": "string",
    "bank_account": "string",
    "notes": "string"
}

Rules:
- All monetary values must be plain numbers (no currency symbols or commas).
- Dates must be in YYYY-MM-DD format when possible; keep original if ambiguous.
- If a field is not present, use null.
- Do NOT invent or guess data that is not in the image.
"""

MULTI_PAGE_MERGE_PROMPT = """You are given JSON extracted from multiple pages of the same invoice.
Merge them into a single coherent JSON object. Line items from all pages must be combined.
Prefer values from later pages when there are duplicates (except for line items — accumulate all).

Return ONLY the merged JSON object with no explanation.
"""


class InvoiceProcessorAgent:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "anthropic").lower()

        if self.provider == "anthropic":
            self._init_claude()
        elif self.provider == "gemini":
            self._init_gemini()
        else:
            raise ValueError(
                f"Unknown AI_PROVIDER '{self.provider}'. Set AI_PROVIDER to 'anthropic' or 'gemini'."
            )

    # ── Provider Init ──────────────────────────────────────────────────────────

    def _init_claude(self):
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        self.claude_client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        print(f"  Provider : Anthropic Claude | Model: {self.model}")

    def _init_gemini(self):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY is not set. Add it to your .env file.")
        genai.configure(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        self.gemini_client = genai.GenerativeModel(self.model)
        print(f"  Provider : Google Gemini | Model: {self.model}")

    # ── Extraction ─────────────────────────────────────────────────────────────

    def _extract_from_image(self, image_bytes: bytes, media_type: str = "image/png") -> dict:
        """Dispatch to the correct provider and return extracted JSON dict."""
        if self.provider == "anthropic":
            return self._extract_claude(image_bytes, media_type)
        return self._extract_gemini(image_bytes)

    def _extract_claude(self, image_bytes: bytes, media_type: str) -> dict:
        message = self.claude_client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": image_to_base64(image_bytes, media_type),
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )
        return self._parse_json(message.content[0].text.strip())

    def _extract_gemini(self, image_bytes: bytes) -> dict:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        response = self.gemini_client.generate_content([EXTRACTION_PROMPT, img])
        return self._parse_json(response.text.strip())

    # ── Multi-page merge ───────────────────────────────────────────────────────

    def _merge_pages(self, page_results: List[dict]) -> dict:
        """Merge multi-page extraction results into one using the AI."""
        if len(page_results) == 1:
            return page_results[0]

        combined = json.dumps(page_results, indent=2)
        prompt = f"{MULTI_PAGE_MERGE_PROMPT}\n\nPages JSON:\n{combined}"

        if self.provider == "anthropic":
            message = self.claude_client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
        else:
            response = self.gemini_client.generate_content(prompt)
            raw = response.text.strip()

        return self._parse_json(raw)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict:
        """Safely parse JSON — strips markdown fences if the model adds them."""
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
        return json.loads(cleaned)

    def _dict_to_invoice_data(self, data: dict) -> InvoiceData:
        line_items = [
            LineItem(
                description=str(item.get("description", "")),
                quantity=self._to_float(item.get("quantity")),
                unit_price=self._to_float(item.get("unit_price")),
                total=self._to_float(item.get("total")),
            )
            for item in data.get("line_items", [])
        ]
        return InvoiceData(
            vendor_name=data.get("vendor_name"),
            vendor_address=data.get("vendor_address"),
            vendor_email=data.get("vendor_email"),
            vendor_phone=data.get("vendor_phone"),
            vendor_tax_id=data.get("vendor_tax_id"),
            client_name=data.get("client_name"),
            client_address=data.get("client_address"),
            client_email=data.get("client_email"),
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            due_date=data.get("due_date"),
            purchase_order_number=data.get("purchase_order_number"),
            currency=data.get("currency"),
            line_items=line_items,
            subtotal=self._to_float(data.get("subtotal")),
            tax_rate=self._to_float(data.get("tax_rate")),
            tax_amount=self._to_float(data.get("tax_amount")),
            discount=self._to_float(data.get("discount")),
            shipping=self._to_float(data.get("shipping")),
            total_amount=self._to_float(data.get("total_amount")),
            payment_terms=data.get("payment_terms"),
            payment_method=data.get("payment_method"),
            bank_account=data.get("bank_account"),
            notes=data.get("notes"),
        )

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    # ── Main entry point ───────────────────────────────────────────────────────

    def process(self, file_bytes: bytes, filename: str) -> tuple[InvoiceData, int]:
        """Returns (InvoiceData, pages_processed). Handles PDF and image files."""
        ext = get_file_extension(filename)
        page_results = []

        if ext == "pdf":
            page_images = pdf_to_images(file_bytes)
            for page_img in page_images:
                result = self._extract_from_image(page_img, "image/png")
                page_results.append(result)
        else:
            norm_bytes, media_type = normalize_image(file_bytes, filename)
            result = self._extract_from_image(norm_bytes, media_type)
            page_results.append(result)

        merged = self._merge_pages(page_results)
        invoice_data = self._dict_to_invoice_data(merged)
        return invoice_data, len(page_results)
