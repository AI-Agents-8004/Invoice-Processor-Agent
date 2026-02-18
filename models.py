from pydantic import BaseModel
from typing import Optional, List


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class InvoiceData(BaseModel):
    # Vendor / Seller
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    vendor_tax_id: Optional[str] = None

    # Client / Buyer
    client_name: Optional[str] = None
    client_address: Optional[str] = None
    client_email: Optional[str] = None

    # Invoice Meta
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    purchase_order_number: Optional[str] = None
    currency: Optional[str] = None

    # Line Items
    line_items: List[LineItem] = []

    # Totals
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    discount: Optional[float] = None
    shipping: Optional[float] = None
    total_amount: Optional[float] = None

    # Payment
    payment_terms: Optional[str] = None
    payment_method: Optional[str] = None
    bank_account: Optional[str] = None

    # Extras
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    success: bool
    invoice_id: str
    filename: str
    pages_processed: int = 1
    data: Optional[InvoiceData] = None
    error: Optional[str] = None
    processing_time_ms: int


class HealthResponse(BaseModel):
    status: str
    model: str
    version: str
