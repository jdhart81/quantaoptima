import copy
import hashlib
import hmac
import io
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import stripe_webhook as webhook
from quantaoptima.licensing import validate_license_key
from test_licensing import issuer


@pytest.fixture
def billing(issuer, tmp_path, monkeypatch):
    monkeypatch.setattr(webhook, 'DELIVERY_DB', str(tmp_path / 'billing.sqlite3'))
    monkeypatch.setattr(webhook, 'PRO_PRICE_IDS', {'price_pro'})
    monkeypatch.setattr(webhook, 'WEBHOOK_SECRET', 'whsec_review_fixture')
    line = {'amount': 2900, 'parent': {'type': 'subscription_item_details', 'subscription_item_details': {'subscription': 'sub_review'}},
            'pricing': {'price_details': {'price': 'price_pro'}}, 'period': {'end': int(time.time())+30*86400}}
    client = Mock()
    client.v1.subscriptions.retrieve.return_value = {'status': 'active'}
    client.v1.invoices.list_lines.return_value.auto_paging_iter.side_effect = lambda: iter([line])
    monkeypatch.setattr(webhook, '_client', lambda: client)
    sender = Mock(return_value=True)
    monkeypatch.setattr(webhook, '_send_license_email', sender)
    event = {'object': 'event', 'id': 'evt_review', 'type': 'invoice.paid', 'data': {'object': {
        'object': 'invoice', 'id': 'in_review', 'status': 'paid', 'customer_email': 'review@example.invalid',
        'parent': {'subscription_details': {'subscription': 'sub_review'}}}}}
    return event, line, client, sender


def test_initial_invoice_and_renewal_are_fulfilled(billing):
    event, line, client, sender = billing
    webhook.handle_invoice_paid(event)
    first = validate_license_key(sender.call_args.args[1])
    assert first.valid
    assert first.expires == line['period']['end'] + webhook.GRACE_SECONDS
    event['data']['object']['id'] = 'in_renewal'
    line['period']['end'] += 30*86400
    webhook.handle_invoice_paid(event)
    assert sender.call_count == 2
    assert validate_license_key(sender.call_args.args[1]).expires == first.expires + 30*86400


def test_duplicate_invoice_does_not_redeliver(billing):
    event, _, _, sender = billing
    webhook.handle_invoice_paid(event)
    event['id'] = 'evt_another_notification_for_same_invoice'
    assert webhook.handle_invoice_paid(event)['status'] == 'duplicate'
    assert sender.call_count == 1


def test_failed_email_retries_same_persisted_token(billing):
    event, _, _, sender = billing
    sender.return_value = False
    with pytest.raises(RuntimeError, match='delivery failed'):
        webhook.handle_invoice_paid(event)
    first_token = sender.call_args.args[1]
    sender.return_value = True
    webhook.handle_invoice_paid(event)
    assert sender.call_args.args[1] == first_token


def test_old_paid_invoice_cannot_extend_or_replace_new_access(billing):
    event, line, _, sender = billing
    webhook.handle_invoice_paid(event)
    event['data']['object']['id'] = 'in_older'
    line['period']['end'] -= 15*86400
    assert webhook.handle_invoice_paid(event)['status'] == 'ignored'
    assert sender.call_count == 1


@pytest.mark.parametrize('change', ['unpaid', 'wrong_price', 'one_time_line', 'inactive', 'wrong_subscription'])
def test_nonqualifying_invoices_never_issue(billing, change):
    event, line, client, sender = billing
    if change == 'unpaid': event['data']['object']['status'] = 'open'
    if change == 'wrong_price': line['pricing']['price_details']['price'] = 'price_other'
    if change == 'one_time_line': line['parent'] = {'type': 'invoice_item_details'}
    if change == 'inactive': client.v1.subscriptions.retrieve.return_value = {'status': 'canceled'}
    if change == 'wrong_subscription': line['parent']['subscription_item_details']['subscription'] = 'sub_other'
    assert webhook.handle_invoice_paid(event)['status'] == 'ignored'
    sender.assert_not_called()


def test_checkout_waits_for_paid_invoice(billing):
    event, _, _, sender = billing
    assert webhook.handle_checkout_completed(event)['status'] == 'ignored'
    sender.assert_not_called()


class Request:
    _respond = webhook.StripeWebhookHandler._respond
    def __init__(self, payload, signature=''):
        self.headers = {'Content-Length': str(len(payload)), 'Stripe-Signature': signature}
        self.rfile, self.wfile = io.BytesIO(payload), io.BytesIO()
    def send_response(self, code): self.code = code
    def send_header(self, *args): pass
    def end_headers(self): pass


def request(event, signed=True):
    payload = json.dumps(event).encode()
    timestamp = int(time.time())
    signature = hmac.new(webhook.WEBHOOK_SECRET.encode(), str(timestamp).encode()+b'.'+payload, hashlib.sha256).hexdigest()
    return Request(payload, f't={timestamp},v1={signature}' if signed else '')


def test_real_signature_verification_and_delivery_failure_retry(billing):
    event, _, _, sender = billing
    sender.return_value = False
    req = request(event)
    webhook.StripeWebhookHandler.do_POST(req)
    assert req.code == 500
    sender.return_value = True
    req = request(event)
    webhook.StripeWebhookHandler.do_POST(req)
    assert req.code == 200


def test_unsigned_request_rejected(billing):
    event, _, _, sender = billing
    req = request(event, signed=False)
    webhook.StripeWebhookHandler.do_POST(req)
    assert req.code == 400
    sender.assert_not_called()


def test_missing_webhook_secret_fails_closed(billing, monkeypatch):
    event, _, _, sender = billing
    monkeypatch.setattr(webhook, 'WEBHOOK_SECRET', '')
    req = request(event, signed=False)
    webhook.StripeWebhookHandler.do_POST(req)
    assert req.code == 503
    sender.assert_not_called()


def test_startup_requires_complete_config(monkeypatch):
    monkeypatch.setattr(webhook, 'WEBHOOK_SECRET', '')
    with pytest.raises(ValueError, match='STRIPE_WEBHOOK_SECRET'):
        webhook.validate_config()
