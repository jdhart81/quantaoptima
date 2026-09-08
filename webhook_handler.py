#!/usr/bin/env python3
"""The legacy unauthenticated Gumroad fulfillment endpoint is retired.

Use the verified Stripe service in stripe_webhook.py. For an existing Gumroad
purchase, reconcile the sale manually before issuing a v2 license through the
administrator CLI. This endpoint must never mint licenses from form data.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import os


def handle_gumroad_webhook(body):
    return {'status': 'retired', 'message': 'Automatic Gumroad fulfillment is disabled'}


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(410)
        self.end_headers()
        self.wfile.write(b'Legacy fulfillment retired; contact support')


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))), WebhookHandler).serve_forever()
