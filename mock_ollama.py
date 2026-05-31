from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class MockOllama(BaseHTTPRequestHandler):
    def do_POST(self):
        # Return a response shaped like the real agents expect: a <file> block for the
        # PR Engineer to apply, plus the exact marker the CodeReviewer checks for.
        response = {
            "model": "qwen2.5:0.5b",
            "created_at": "2023-10-10T10:00:00Z",
            "response": (
                "Here is the fix:\n"
                "<file path=\"test_fix.py\">\n"
                "def test_fix():\n"
                "    return 'Hello from Mock AI'\n"
                "</file>\n\n"
                "[FINAL_STATUS: APPROVED]"
            ),
            "done": True
        }
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Suppress logging
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(('localhost', 11434), MockOllama)
    print("Mock Ollama API running on port 11434...")
    server.serve_forever()
