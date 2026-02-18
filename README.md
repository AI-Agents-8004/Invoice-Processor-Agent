# Invoice Processor Agent

An AI-powered invoice data extraction agent that converts unstructured invoice files (PDFs and images) into clean, structured data. Built with FastAPI and powered by Claude (Anthropic) or Gemini (Google), it exposes REST, A2A (Agent-to-Agent), and MCP (Model Context Protocol) endpoints — making it consumable by humans, applications, and other AI agents.

---

## Live Deployment

| | URL |
|---|---|
| **Base URL** | `https://invoice-processor-agent.onrender.com` |
| **API Docs** | `https://invoice-processor-agent.onrender.com/docs` |
| **Health Check** | `https://invoice-processor-agent.onrender.com/health` |
| **Process Invoice** | `https://invoice-processor-agent.onrender.com/process` |
| **A2A Agent Card** | `https://invoice-processor-agent.onrender.com/.well-known/agent.json` |
| **A2A Task Endpoint** | `https://invoice-processor-agent.onrender.com/a2a` |
| **MCP Endpoint** | `https://invoice-processor-agent.onrender.com/sse` |

---

## Table of Contents

- [What It Does](#what-it-does)
- [Features](#features)
- [Architecture](#architecture)
- [Extracted Data Fields](#extracted-data-fields)
- [API Reference](#api-reference)
  - [GET /health](#get-health)
  - [POST /process](#post-process)
  - [GET /.well-known/agent.json](#get-well-knownagentjson)
  - [POST /a2a](#post-a2a)
  - [GET /sse](#get-sse)
- [Output Formats](#output-formats)
- [MCP Integration](#mcp-integration)
- [A2A Integration](#a2a-integration)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Error Handling](#error-handling)

---

## What It Does

Users upload an invoice — a scanned PDF, a photo, or any image format — and the agent uses AI vision to read and extract every piece of information on it. The raw, unstructured document is converted into a structured JSON object that any application can immediately consume.

**Input:** Invoice file (PDF, PNG, JPG, JPEG, WEBP, TIFF) — up to 20 MB, multi-page PDFs supported.

**Output:** Structured data as JSON response, downloadable CSV, or formatted Excel spreadsheet.

```
Invoice PDF/Image
      ↓
AI Vision (Claude or Gemini)
      ↓
Structured JSON / CSV / Excel
```

---

## Features

- **Multi-format input** — Accepts PDF, PNG, JPG, JPEG, WEBP, and TIFF files
- **Multi-page PDF support** — Processes every page and merges results into one response
- **Three output formats** — JSON (API response), CSV (download), Excel (download)
- **Dual AI provider support** — Switch between Anthropic Claude and Google Gemini via a single environment variable
- **REST API** — Standard HTTP endpoint for application integrations
- **A2A Protocol** — Google Agent-to-Agent protocol support for agent-to-agent communication
- **MCP Protocol** — Model Context Protocol support for Claude Desktop, Cursor, Windsurf, and other MCP clients
- **Interactive docs** — Auto-generated Swagger UI at `/docs`

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐  │
│  │  /process │  │  /a2a    │  │ /.well-  │  │ /sse  │  │
│  │  REST API │  │  A2A     │  │  known/  │  │  MCP  │  │
│  └──────────┘  └──────────┘  │agent.json│  └───────┘  │
│                               └──────────┘              │
│                      ↓                                  │
│            InvoiceProcessorAgent                        │
│                      ↓                                  │
│     ┌────────────────────────────────┐                  │
│     │  AI Provider (switchable)      │                  │
│     │  ├── Anthropic Claude          │                  │
│     │  └── Google Gemini             │                  │
│     └────────────────────────────────┘                  │
│                      ↓                                  │
│            Structured InvoiceData                       │
│                      ↓                                  │
│     ┌──────────────────────────────┐                    │
│     │  Export Layer                │                    │
│     │  ├── JSON response           │                    │
│     │  ├── CSV download            │                    │
│     │  └── Excel download          │                    │
│     └──────────────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

**File breakdown:**

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, all routes, MCP mount, A2A endpoints |
| `agent.py` | Core AI logic, provider abstraction (Claude / Gemini) |
| `models.py` | Pydantic data models (InvoiceData, LineItem, etc.) |
| `utils.py` | PDF→image conversion, file validation, base64 encoding |
| `exports.py` | CSV and Excel generation |
| `mcp_server.py` | Standalone MCP server (for local stdio use with Claude Desktop) |

---

## Extracted Data Fields

The agent attempts to extract the following fields from every invoice:

### Vendor Information
| Field | Description |
|---|---|
| `vendor_name` | Name of the selling company or individual |
| `vendor_address` | Full address of the vendor |
| `vendor_email` | Vendor contact email |
| `vendor_phone` | Vendor contact phone number |
| `vendor_tax_id` | Tax ID, VAT number, or EIN |

### Client Information
| Field | Description |
|---|---|
| `client_name` | Name of the buying company or individual |
| `client_address` | Full address of the client |
| `client_email` | Client contact email |

### Invoice Metadata
| Field | Description |
|---|---|
| `invoice_number` | Unique invoice identifier |
| `invoice_date` | Date the invoice was issued (YYYY-MM-DD) |
| `due_date` | Payment due date (YYYY-MM-DD) |
| `purchase_order_number` | Associated PO number if present |
| `currency` | 3-letter ISO currency code (e.g. USD, EUR, GBP) |

### Line Items
Each item in the `line_items` array contains:
| Field | Description |
|---|---|
| `description` | Product or service description |
| `quantity` | Number of units |
| `unit_price` | Price per unit |
| `total` | Line total (quantity × unit price) |

### Totals & Taxes
| Field | Description |
|---|---|
| `subtotal` | Sum before tax and discounts |
| `tax_rate` | Tax percentage |
| `tax_amount` | Absolute tax amount |
| `discount` | Discount applied |
| `shipping` | Shipping charges |
| `total_amount` | Final amount due |

### Payment Details
| Field | Description |
|---|---|
| `payment_terms` | e.g. "Net 30", "Due on receipt" |
| `payment_method` | e.g. "Bank Transfer", "Credit Card" |
| `bank_account` | Bank account or routing details |
| `notes` | Any additional notes on the invoice |

> All monetary values are returned as plain numbers with no currency symbols. Missing fields are returned as `null`.

---

## API Reference

### GET /health

Returns the current status of the agent.

**Request**
```bash
curl https://invoice-processor-agent.onrender.com/health
```

**Response**
```json
{
  "status": "ok",
  "model": "gemini-1.5-pro",
  "version": "1.3.0"
}
```

---

### POST /process

Uploads an invoice file and returns extracted data.

**URL:** `https://invoice-processor-agent.onrender.com/process`
**Method:** `POST`
**Content-Type:** `multipart/form-data`

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `format` | string | `json` | Output format: `json` \| `csv` \| `excel` |

**Form Fields**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | Invoice file (PDF, PNG, JPG, JPEG, WEBP, TIFF). Max 20 MB. |

---

**Example 1 — JSON response**

```bash
curl -X POST "https://invoice-processor-agent.onrender.com/process?format=json" \
  -F "file=@invoice.pdf"
```

```json
{
  "success": true,
  "invoice_id": "a3f9c2d1-84b2-4e91-bc3a-f0d12e4567ab",
  "filename": "invoice.pdf",
  "pages_processed": 1,
  "processing_time_ms": 2340,
  "data": {
    "vendor_name": "Acme Corp Ltd",
    "vendor_address": "123 Business Ave, New York, NY 10001",
    "vendor_email": "billing@acmecorp.com",
    "vendor_phone": "+1 (555) 123-4567",
    "vendor_tax_id": "US-12-3456789",
    "client_name": "TechStart Inc.",
    "client_address": "456 Startup Road, San Francisco, CA 94107",
    "client_email": "accounts@techstart.io",
    "invoice_number": "INV-2024-0042",
    "invoice_date": "2024-03-15",
    "due_date": "2024-04-14",
    "purchase_order_number": "PO-9981",
    "currency": "USD",
    "line_items": [
      {
        "description": "Web Development Services (March 2024)",
        "quantity": 40,
        "unit_price": 150.00,
        "total": 6000.00
      },
      {
        "description": "UI/UX Design Consultation",
        "quantity": 8,
        "unit_price": 200.00,
        "total": 1600.00
      }
    ],
    "subtotal": 8399.00,
    "tax_rate": 10,
    "tax_amount": 839.90,
    "discount": 200.00,
    "shipping": null,
    "total_amount": 9038.90,
    "payment_terms": "Net 30",
    "payment_method": "Bank Transfer",
    "bank_account": "Routing: 021000021 | Account: 987654321",
    "notes": null
  }
}
```

---

**Example 2 — Download CSV**

```bash
curl -X POST "https://invoice-processor-agent.onrender.com/process?format=csv" \
  -F "file=@invoice.pdf" \
  -o invoice_data.csv
```

Downloads `invoice_data.csv` with invoice summary and line items sections.

---

**Example 3 — Download Excel**

```bash
curl -X POST "https://invoice-processor-agent.onrender.com/process?format=excel" \
  -F "file=@invoice.pdf" \
  -o invoice_data.xlsx
```

Downloads `invoice_data.xlsx` with two sheets:
- **Sheet 1** — Invoice Summary (styled, color-coded sections)
- **Sheet 2** — Line Items (table with totals row)

---

### GET /.well-known/agent.json

Returns the A2A Agent Card — a standardized description of this agent's identity, capabilities, and skills. Other AI agents use this endpoint to discover and understand how to interact with this agent.

**Request**
```bash
curl https://invoice-processor-agent.onrender.com/.well-known/agent.json
```

**Response**
```json
{
  "name": "Invoice Processor Agent",
  "description": "Extracts structured data from invoice PDFs and images using AI vision.",
  "url": "https://invoice-processor-agent.onrender.com",
  "version": "1.3.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "process_invoice",
      "name": "Process Invoice",
      "tags": ["invoice", "ocr", "finance", "accounting", "data-extraction"]
    }
  ]
}
```

---

### POST /a2a

Google Agent-to-Agent (A2A) Protocol endpoint. Accepts JSON-RPC 2.0 requests. Other AI agents send tasks here to invoke the invoice processing capability.

**URL:** `https://invoice-processor-agent.onrender.com/a2a`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "id": "1",
  "params": {
    "id": "task-uuid-here",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "file",
          "file": {
            "name": "invoice.pdf",
            "mimeType": "application/pdf",
            "bytes": "<base64-encoded-file-content>"
          }
        }
      ]
    }
  }
}
```

**Example**
```bash
# Encode your invoice to base64 first
BASE64=$(base64 -i invoice.pdf)

# Send A2A task
curl -X POST https://invoice-processor-agent.onrender.com/a2a \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tasks/send\",
    \"id\": \"1\",
    \"params\": {
      \"id\": \"task-001\",
      \"message\": {
        \"role\": \"user\",
        \"parts\": [{
          \"type\": \"file\",
          \"file\": {
            \"name\": \"invoice.pdf\",
            \"mimeType\": \"application/pdf\",
            \"bytes\": \"$BASE64\"
          }
        }]
      }
    }
  }"
```

**Response**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-001",
    "status": {
      "state": "completed",
      "timestamp": "2024-03-15T14:22:10Z"
    },
    "artifacts": [
      {
        "name": "invoice_data",
        "description": "Extracted data from invoice.pdf (1 page(s))",
        "parts": [
          {
            "type": "data",
            "data": {
              "vendor_name": "Acme Corp Ltd",
              "total_amount": 9038.90
            }
          }
        ]
      }
    ]
  }
}
```

---

### GET /sse

MCP (Model Context Protocol) endpoint using SSE (Server-Sent Events) transport. This is not a browser-accessible URL — it is consumed by MCP-compatible clients such as Claude Desktop, Cursor, and Windsurf.

**URL:** `https://invoice-processor-agent.onrender.com/sse`

See the [MCP Integration](#mcp-integration) section below for client setup instructions.

---

## Output Formats

| Format | How to request | Use case |
|---|---|---|
| `json` | `?format=json` (default) | Application integrations, APIs |
| `csv` | `?format=csv` | Accountants, data analysts |
| `excel` | `?format=excel` | Business users, reporting, finance teams |

---

## MCP Integration

MCP (Model Context Protocol) lets AI assistants like Claude Desktop use this agent as a native tool — without any code on the client side.

### Option A — Remote URL (Claude Desktop, Cursor, Windsurf)

Add the following to your MCP client config:

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`
**Cursor** — `.cursor/mcp.json`
**Windsurf** — `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "invoice-processor": {
      "url": "https://invoice-processor-agent.onrender.com/sse"
    }
  }
}
```

Restart your client. You can then say:
> *"Process this invoice and tell me the total amount"*
> *"Extract all line items from the attached invoice PDF"*

The assistant will call this agent automatically.

---

### Option B — Local stdio (Claude Desktop only)

For running the MCP server locally using stdio transport:

```json
{
  "mcpServers": {
    "invoice-processor": {
      "command": "python",
      "args": ["/path/to/agents/invoice-processor-agent/mcp_server.py"],
      "env": {
        "AI_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "sk-ant-api03-..."
      }
    }
  }
}
```

### Exposed MCP Tools

| Tool | Description |
|---|---|
| `process_invoice_mcp` | Extract structured data from a base64-encoded invoice file |
| `get_supported_formats` | Returns supported file formats and current model info |

---

## A2A Integration

This agent implements the [Google Agent-to-Agent (A2A) Protocol](https://google.github.io/A2A). Other AI agents can:

1. **Discover** the agent via `GET /.well-known/agent.json`
2. **Send tasks** via `POST /a2a` using JSON-RPC 2.0
3. **Receive structured results** directly in the response (stateless — no polling needed)

**Supported A2A methods:**

| Method | Description |
|---|---|
| `tasks/send` | Send an invoice file for processing and receive results immediately |

---

## Local Development

### Prerequisites

- Python 3.11+
- Anthropic API key or Google Gemini API key

### Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd invoice-processor-agent

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your API key
```

### Run

```bash
# Start the main server (REST + A2A + MCP all on port 8000)
python main.py
```

Server starts at `http://localhost:8000`

### Generate a Sample Invoice for Testing

```bash
pip install reportlab
python tests/create_sample_invoice.py
# Creates tests/sample_invoice.pdf
```

### Test

```bash
# Process sample invoice (JSON)
curl -X POST http://localhost:8000/process \
  -F "file=@tests/sample_invoice.pdf" | python3 -m json.tool

# Download as CSV
curl -X POST "http://localhost:8000/process?format=csv" \
  -F "file=@tests/sample_invoice.pdf" \
  -o output.csv

# Download as Excel
curl -X POST "http://localhost:8000/process?format=excel" \
  -F "file=@tests/sample_invoice.pdf" \
  -o output.xlsx

# Run unit tests
pip install pytest
pytest tests/ -v

# Run integration tests (server must be running)
BASE_URL=http://localhost:8000 pytest tests/ -v
```

### Run with Docker

```bash
# Build and start
docker compose up --build

# Server available at http://localhost:8000
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# ── AI Provider ────────────────────────────────────────
# Choose one: anthropic | gemini
AI_PROVIDER=anthropic

# ── Anthropic Claude (if AI_PROVIDER=anthropic) ────────
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
CLAUDE_MODEL=claude-sonnet-4-6

# ── Google Gemini (if AI_PROVIDER=gemini) ──────────────
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-1.5-pro

# ── App ────────────────────────────────────────────────
APP_ENV=development
MAX_FILE_SIZE_MB=20
PORT=8000
HOST=0.0.0.0
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | Yes | `anthropic` | AI provider: `anthropic` or `gemini` |
| `ANTHROPIC_API_KEY` | If using Claude | — | Anthropic API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-6` | Claude model ID |
| `GEMINI_API_KEY` | If using Gemini | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-1.5-pro` | Gemini model ID |
| `MAX_FILE_SIZE_MB` | No | `20` | Maximum upload file size in MB |
| `APP_ENV` | No | `development` | `development` enables hot reload |
| `PORT` | No | `8000` | Server port |

---

## Deployment

### Render (Recommended)

1. Push code to a GitHub repository
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your GitHub repository
4. Render auto-detects the `Dockerfile` and configures the build
5. Add environment variables under **Settings → Environment**:
   - `AI_PROVIDER` = `anthropic` or `gemini`
   - `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` = your key
6. Click **Deploy**

> **Free tier note:** Render free tier spins down services after 15 minutes of inactivity. The first request after a sleep period may take up to 30 seconds. Upgrade to a paid plan for always-on availability.

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up

# Set environment variables
railway variables set AI_PROVIDER=anthropic
railway variables set ANTHROPIC_API_KEY=sk-ant-...
```

### Fly.io

```bash
fly launch        # auto-detects Dockerfile
fly secrets set AI_PROVIDER=anthropic
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

---

## Project Structure

```
invoice-processor-agent/
├── main.py                    # FastAPI app — REST, A2A, and MCP endpoints
├── agent.py                   # Core AI agent — Claude and Gemini provider support
├── models.py                  # Pydantic models — InvoiceData, LineItem, responses
├── utils.py                   # Utilities — PDF conversion, validation, base64
├── exports.py                 # Export generators — CSV and Excel
├── mcp_server.py              # Standalone MCP server for local stdio use
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local Docker Compose setup
├── .env.example               # Environment variable template
└── tests/
    ├── test_agent.py          # Unit and integration tests
    └── create_sample_invoice.py  # Generates a sample PDF for testing
```

---

## Error Handling

All errors from the `/process` endpoint return a consistent JSON structure:

```json
{
  "success": false,
  "invoice_id": "uuid",
  "filename": "invoice.pdf",
  "error": "Description of what went wrong",
  "processing_time_ms": 120
}
```

**Common errors:**

| Situation | HTTP Status | Error message |
|---|---|---|
| Unsupported file type | `422` | `File type '.docx' not supported` |
| File too large | `422` | `File too large (25.0 MB). Maximum allowed: 20 MB` |
| Missing API key | `500` | `ANTHROPIC_API_KEY is not set` |
| Corrupted file | `500` | `Processing failed: ...` |

**A2A errors** follow JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32602,
    "message": "No file part found in message"
  }
}
```

| Code | Meaning |
|---|---|
| `-32700` | Parse error — invalid JSON |
| `-32601` | Method not found |
| `-32602` | Invalid params — missing or bad file |
| `-32603` | Internal error — processing failed |

---

## Supported File Formats

| Format | Extension | Notes |
|---|---|---|
| PDF | `.pdf` | Multi-page supported — all pages processed and merged |
| PNG | `.png` | |
| JPEG | `.jpg`, `.jpeg` | |
| WebP | `.webp` | |
| TIFF | `.tiff` | |

**Maximum file size:** 20 MB (configurable via `MAX_FILE_SIZE_MB`)
