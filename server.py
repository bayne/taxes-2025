"""
Simple HTTP server for the tax calculator web UI.

Serves static files and provides a /api/calculate endpoint.
No dependencies beyond the standard library.

Usage:
    uv run python server.py
    # Then open http://localhost:8000
"""

import http.server
import json
import os
import sys
from dataclasses import asdict

from calculator import ValidationError, _deserialize_enum, calculate
from models import TaxReturnInput, generate_schema


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class TaxHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/calculate":
            self._handle_calculate()
        elif self.path == "/api/schema":
            self._handle_schema()
        elif self.path == "/api/pdf":
            self._handle_pdf()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == "/api/schema":
            self._handle_schema()
        else:
            # Serve index.html for all non-file paths (SPA routing)
            if not os.path.exists(os.path.join(STATIC_DIR, self.path.lstrip("/"))):
                self.path = "/index.html"
            super().do_GET()

    def _handle_calculate(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            _deserialize_enum(data, TaxReturnInput)
            inp = TaxReturnInput(**data)
            result = calculate(inp)

            response = json.dumps(asdict(result), indent=2, default=str)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())

        except ValidationError as e:
            error_response = json.dumps({"errors": [str(e)]})
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response.encode())

        except Exception as e:
            error_response = json.dumps({"errors": [str(e)]})
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response.encode())

    def _handle_pdf(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            # Optional: caller may request a single form instead of the full ZIP
            single_form_id = data.pop("_form_id", None)

            _deserialize_enum(data, TaxReturnInput)
            inp = TaxReturnInput(**data)
            result = calculate(inp)

            from dataclasses import asdict
            from enum import Enum

            def _enum_to_str(obj):
                if isinstance(obj, dict):
                    return {k: _enum_to_str(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_enum_to_str(v) for v in obj]
                if isinstance(obj, Enum):
                    return obj.name
                return obj

            input_dict = _enum_to_str(asdict(inp))
            output_dict = _enum_to_str(asdict(result))

            if single_form_id:
                # Return a single PDF inline so the browser can display it
                from pdf_filler import fill_form
                pdf_bytes = fill_form(single_form_id, input_dict, output_dict)
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f"inline; filename={single_form_id}_filled.pdf")
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.end_headers()
                self.wfile.write(pdf_bytes)
            else:
                # Return a ZIP of all applicable forms; include the list in a header
                from pdf_filler import fill_return_zip, determine_required_forms
                form_ids = determine_required_forms(input_dict, output_dict)
                zip_bytes = fill_return_zip(input_dict, output_dict, form_ids)
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", "attachment; filename=tax_return.zip")
                self.send_header("Content-Length", str(len(zip_bytes)))
                self.send_header("X-Form-Ids", ",".join(form_ids))
                self.end_headers()
                self.wfile.write(zip_bytes)

        except ImportError:
            error_response = json.dumps({"errors": ["pypdf is required for PDF generation. Install with: uv sync --group pdf"]})
            self.send_response(501)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response.encode())

        except ValidationError as e:
            error_response = json.dumps({"errors": [str(e)]})
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response.encode())

        except Exception as e:
            error_response = json.dumps({"errors": [str(e)]})
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response.encode())

    def _handle_schema(self):
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        response = json.dumps(schema, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        # Quieter logging
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = http.server.HTTPServer(("0.0.0.0", port), TaxHandler)
    print(f"Tax Calculator running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
