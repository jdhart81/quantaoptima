import base64
import hashlib
import hmac
import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from quantaoptima.licensing import generate_license_key, validate_license_key, load_license, clear_license_cache


@pytest.fixture
def issuer(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    (tmp_path / 'private.pem').write_bytes(private)
    (tmp_path / 'public.pem').write_bytes(public)
    monkeypatch.setenv('QUANTAOPTIMA_LICENSE_PRIVATE_KEY_FILE', str(tmp_path / 'private.pem'))
    monkeypatch.setenv('QUANTAOPTIMA_LICENSE_PUBLIC_KEY_FILE', str(tmp_path / 'public.pem'))
    clear_license_cache()
    yield private, public
    clear_license_cache()


def test_paid_key_verifies_without_disclosing_private_key(issuer, monkeypatch):
    token = generate_license_key('pro', 'review@example.invalid')
    monkeypatch.delenv('QUANTAOPTIMA_LICENSE_PRIVATE_KEY_FILE')
    result = validate_license_key(token)
    assert result.valid and result.tier == 'pro'


def test_public_key_cannot_mint_license(issuer):
    with pytest.raises(ValueError):
        generate_license_key('enterprise', 'review@example.invalid', signing_key=issuer[1])


def test_no_default_signing_key(monkeypatch):
    monkeypatch.delenv('QUANTAOPTIMA_LICENSE_PRIVATE_KEY_FILE', raising=False)
    with pytest.raises(ValueError):
        generate_license_key('enterprise', 'review@example.invalid')


def test_reject_publicly_forgeable_legacy_license(issuer):
    payload = base64.urlsafe_b64encode(json.dumps({'tier': 'enterprise', 'email': 'review@example.invalid', 'expires': 0}).encode()).decode()
    signature = hmac.new(b'quantaoptima-community-edition-2025', payload.encode(), hashlib.sha256).hexdigest()
    result = validate_license_key(payload + '.' + signature)
    assert not result.valid
    assert result.tier == 'community'


def test_tampered_license_rejected(issuer):
    token = generate_license_key('pro', 'review@example.invalid')
    prefix, payload, signature = token.split('.')
    decoded = json.loads(base64.urlsafe_b64decode(payload))
    decoded['tier'] = 'enterprise'
    payload = base64.urlsafe_b64encode(json.dumps(decoded).encode()).decode()
    assert not validate_license_key('.'.join([prefix, payload, signature])).valid


def test_attacker_issuer_rejected(issuer):
    attacker = Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    token = generate_license_key('enterprise', 'review@example.invalid', signing_key=attacker)
    assert not validate_license_key(token).valid


def test_expiry_is_bound_to_paid_period(issuer):
    expires = time.time() + 123
    token = generate_license_key('pro', 'review@example.invalid', expires_at=expires)
    assert validate_license_key(token).expires == expires
    expired = generate_license_key('pro', 'review@example.invalid', expires_at=time.time()-1)
    assert not validate_license_key(expired).valid


@pytest.mark.parametrize('expires', [float('nan'), float('inf'), -1, True])
def test_invalid_expiry_rejected(issuer, expires):
    with pytest.raises(ValueError):
        generate_license_key('pro', 'review@example.invalid', expires_at=expires)


def test_cached_license_still_expires(issuer, monkeypatch):
    now = time.time()
    monkeypatch.setenv('QUANTAOPTIMA_LICENSE', generate_license_key('pro', 'review@example.invalid', expires_at=now+10))
    assert load_license().limits['label'].startswith('Pro')
    monkeypatch.setattr('quantaoptima.licensing.time.time', lambda: now+11)
    assert load_license().limits['label'].startswith('Community')
