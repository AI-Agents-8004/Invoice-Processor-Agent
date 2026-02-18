import base64
import io
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastmcp import FastMCP

load_dotenv()

from agent import InvoiceProcessorAgent
from exports import to_csv, to_excel
from models import HealthResponse, InvoiceResponse
from utils import validate_file

# ── MCP Server (mounted inside FastAPI — same port, same URL) ──────────────────

mcp = FastMCP(
    name="Invoice Processor Agent",
    instructions=(
        "Extracts structured data from invoice files. "
        "Provide a base64-encoded invoice (PDF/PNG/JPG/etc.) and get back "
        "vendor info, client info, line items, totals, and payment details."
    ),
)


@mcp.tool()
def process_invoice_mcp(file_base64: str, filename: str) -> dict:
    """
    Extract structured data from an invoice file.

    Args:
        file_base64: Base64-encoded invoice file (PDF, PNG, JPG, JPEG, WEBP, TIFF).
        filename:    Original filename with extension e.g. invoice.pdf

    Returns:
        pages_processed and full structured invoice data.
    """
    import base64 as b64
    file_bytes = b64.b64decode(file_base64)
    invoice_data, pages = agent.process(file_bytes, filename)
    return {"pages_processed": pages, "data": invoice_data.model_dump()}


# ── Lifespan ───────────────────────────────────────────────────────────────────

agent: InvoiceProcessorAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = InvoiceProcessorAgent()
    print(f"✅ Invoice Processor Agent ready | provider: {agent.provider} | model: {agent.model}")
    yield
    print("🛑 Shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Invoice Processor Agent",
    description=(
        "AI-powered invoice data extraction. Upload any PDF or image invoice "
        "and get structured data back as **JSON**, **CSV**, or **Excel**.\n\n"
        "Exposes **MCP** (`/sse`) and **A2A** (`/a2a`) endpoints on the same URL."
    ),
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP SSE app at /sse — same server, same port, same deployed URL
app.mount("/sse", mcp.sse_app())


# ── Info ───────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root(request: Request):
    base = str(request.base_url).rstrip("/")
    return {
        "name": "Invoice Processor Agent",
        "version": "1.2.0",
        "provider": agent.provider if agent else "not loaded",
        "model": agent.model if agent else "not loaded",
        "endpoints": {
            "docs":       f"{base}/docs",
            "health":     f"{base}/health",
            "process":    f"{base}/process?format=json|csv|excel",
            "a2a_card":   f"{base}/.well-known/agent.json",
            "a2a_tasks":  f"{base}/a2a",
            "mcp":        f"{base}/sse",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
def health():
    return HealthResponse(
        status="ok",
        model=agent.model if agent else "not loaded",
        version="1.3.0",
    )


# ── Core: Process Invoice ──────────────────────────────────────────────────────

@app.post("/process", tags=["Invoice"])
async def process_invoice(
    file: UploadFile = File(...),
    format: Literal["json", "csv", "excel"] = Query(
        default="json",
        description="Output format: **json** (default) | **csv** (download) | **excel** (download)",
    ),
):
    """
    Upload an invoice (PDF, PNG, JPG, JPEG, WEBP, TIFF).

    - `format=json`  → Structured JSON response
    - `format=csv`   → Downloadable `.csv` file
    - `format=excel` → Downloadable formatted `.xlsx` file
    """
    invoice_id = str(uuid.uuid4())
    start = time.time()

    file_bytes = await file.read()

    try:
        validate_file(file.filename, len(file_bytes))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        invoice_data, pages = agent.process(file_bytes, file.filename)
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        if format == "json":
            return InvoiceResponse(
                success=False,
                invoice_id=invoice_id,
                filename=file.filename,
                error=str(e),
                processing_time_ms=elapsed,
            )
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = int((time.time() - start) * 1000)
    base_name = file.filename.rsplit(".", 1)[0]

    if format == "json":
        return InvoiceResponse(
            success=True,
            invoice_id=invoice_id,
            filename=file.filename,
            pages_processed=pages,
            data=invoice_data,
            processing_time_ms=elapsed,
        )

    if format == "csv":
        return StreamingResponse(
            content=io.BytesIO(to_csv(invoice_data, invoice_id)),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_invoice.csv"'},
        )

    if format == "excel":
        return StreamingResponse(
            content=io.BytesIO(to_excel(invoice_data, invoice_id)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_invoice.xlsx"'},
        )


# ── A2A: Agent Card ────────────────────────────────────────────────────────────

@app.get("/.well-known/agent.json", tags=["A2A"])
def agent_card(request: Request):
    """
    Google A2A Agent Card — describes this agent's identity and capabilities.
    Other agents discover this first before sending tasks.
    """
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "name": "Invoice Processor Agent",
        "description": (
            "Extracts structured data from invoice PDFs and images using AI vision. "
            "Returns vendor info, client info, line items, totals, and payment details."
        ),
        "url": base,
        "version": "1.2.0",
        "provider": {
            "organization": "AI Agents Marketplace",
            "url": base,
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "authentication": {
            "schemes": []
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "process_invoice",
                "name": "Process Invoice",
                "description": (
                    "Upload a base64-encoded invoice file (PDF/PNG/JPG/JPEG/WEBP/TIFF) "
                    "and receive fully structured invoice data including vendor, client, "
                    "line items, subtotals, tax, discount, and total amount."
                ),
                "tags": ["invoice", "ocr", "finance", "accounting", "data-extraction"],
                "examples": [
                    "Extract all data from this invoice PDF",
                    "What is the total amount on this invoice?",
                    "List all line items from this invoice image",
                    "Who is the vendor on this invoice?",
                ],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    })


# ── A2A: JSON-RPC Task Endpoint ────────────────────────────────────────────────

@app.post("/a2a", tags=["A2A"])
async def a2a_endpoint(request: Request):
    """
    Google A2A Protocol — JSON-RPC 2.0 task endpoint.

    Send a task with a base64-encoded invoice file and receive structured data.

    Example request body:
    ```json
    {
      "jsonrpc": "2.0",
      "method": "tasks/send",
      "id": "1",
      "params": {
        "id": "task-uuid",
        "message": {
          "role": "user",
          "parts": [
            {
              "type": "file",
              "file": {
                "name": "invoice.pdf",
                "mimeType": "application/pdf",
                "bytes": "<base64-encoded-file>"
              }
            }
          ]
        }
      }
    }
    ```
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})

    rpc_id  = body.get("id")
    method  = body.get("method", "")
    params  = body.get("params", {})

    def rpc_error(code: int, message: str):
        return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}})

    if method not in ("tasks/send",):
        return rpc_error(-32601, f"Method '{method}' not supported. Use 'tasks/send'.")

    # Extract file part from message
    parts = params.get("message", {}).get("parts", [])
    file_part = next((p.get("file") for p in parts if p.get("type") == "file"), None)

    if not file_part:
        return rpc_error(-32602, "No file part found. Send a 'file' part with 'name', 'mimeType', and 'bytes'.")

    filename  = file_part.get("name", "invoice.pdf")
    file_b64  = file_part.get("bytes", "")

    if not file_b64:
        return rpc_error(-32602, "'bytes' field is required and must be a base64-encoded file.")

    try:
        file_bytes = base64.b64decode(file_b64)
        validate_file(filename, len(file_bytes))
    except Exception as e:
        return rpc_error(-32602, f"Invalid file: {e}")

    try:
        invoice_data, pages = agent.process(file_bytes, filename)
    except Exception as e:
        return rpc_error(-32603, f"Processing failed: {e}")

    task_id = params.get("id", str(uuid.uuid4()))

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "id": task_id,
            "status": {
                "state": "completed",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "artifacts": [
                {
                    "name": "invoice_data",
                    "description": f"Extracted data from {filename} ({pages} page(s))",
                    "parts": [
                        {
                            "type": "data",
                            "data": invoice_data.model_dump(),
                        }
                    ],
                }
            ],
        },
    })


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("APP_ENV", "development") == "development",
    )
