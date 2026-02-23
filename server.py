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
    server = http.server.HTTPServer(("localhost", port), TaxHandler)
    print(f"Tax Calculator running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
