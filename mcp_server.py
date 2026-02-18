"""
MCP Server for Invoice Processor Agent
---------------------------------------
Exposes the invoice processor as an MCP tool so any MCP-compatible
client (Claude Desktop, Cursor, Windsurf, etc.) can call it directly.

Run modes:
  stdio  (Claude Desktop):  python mcp_server.py
  http   (remote / URL):    python mcp_server.py --http
"""

import argparse
import base64
import os

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

from agent import InvoiceProcessorAgent

# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="Invoice Processor Agent",
    instructions=(
        "This agent extracts structured data from invoice files. "
        "Provide a base64-encoded invoice file (PDF, PNG, JPG, etc.) "
        "and get back vendor info, client info, line items, totals, and payment details."
    ),
)

_agent: InvoiceProcessorAgent | None = None


def get_agent() -> InvoiceProcessorAgent:
    global _agent
    if _agent is None:
        _agent = InvoiceProcessorAgent()
    return _agent


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def process_invoice(file_base64: str, filename: str) -> dict:
    """
    Extract structured data from an invoice file.

    Args:
        file_base64: Base64-encoded invoice file content.
                     Supported formats: PDF, PNG, JPG, JPEG, WEBP, TIFF.
        filename:    Original filename including extension (e.g., "invoice.pdf").
                     This is used to detect the file type.

    Returns:
        A dictionary containing:
        - pages_processed: number of pages processed
        - data: full structured invoice data (vendor, client, line_items, totals, etc.)
    """
    file_bytes = base64.b64decode(file_base64)
    ag = get_agent()
    invoice_data, pages = ag.process(file_bytes, filename)
    return {
        "pages_processed": pages,
        "data": invoice_data.model_dump(),
    }


@mcp.tool()
def get_supported_formats() -> dict:
    """
    Returns the list of file formats supported by this agent.
    """
    return {
        "supported_formats": ["pdf", "png", "jpg", "jpeg", "webp", "tiff"],
        "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "20")),
        "provider": os.getenv("AI_PROVIDER", "anthropic"),
        "model": os.getenv("CLAUDE_MODEL" if os.getenv("AI_PROVIDER", "anthropic") == "anthropic" else "GEMINI_MODEL", "claude-sonnet-4-6"),
    }


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Invoice Processor MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode (exposes a URL). Default is stdio mode for Claude Desktop.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="HTTP port (default: 8001)")
    args = parser.parse_args()

    if args.http:
        import uvicorn
        print(f"🚀 MCP Server running at http://{args.host}:{args.port}/sse")
        # fastmcp 2.2.x uses SSE transport for HTTP
        asgi_app = mcp.sse_app()
        uvicorn.run(asgi_app, host=args.host, port=args.port)
    else:
        # stdio — used by Claude Desktop, Cursor, Windsurf
        mcp.run(transport="stdio")
