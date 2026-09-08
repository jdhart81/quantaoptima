#!/usr/bin/env python3
"""Issuer administration: generate an Ed25519 keypair, issue or verify licenses.

Private keys stay with the issuer. Customers receive the public PEM through a
trusted channel, separately from their license. Never distribute private keys.
"""
import argparse
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from quantaoptima.licensing import generate_license_key, validate_license_key, TIERS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init-keys', metavar='DIRECTORY', help='Create private.pem and public.pem; refuses to overwrite')
    parser.add_argument('--tier', choices=TIERS, default='pro')
    parser.add_argument('--email')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--validate', metavar='TOKEN')
    parser.add_argument('--batch', metavar='JSON_FILE')
    args = parser.parse_args()
    if args.init_keys:
        directory = Path(args.init_keys).expanduser()
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        private, public = directory / 'private.pem', directory / 'public.pem'
        if private.exists() or public.exists():
            parser.error('Key files already exist; refusing to overwrite')
        key = Ed25519PrivateKey.generate()
        with os.fdopen(os.open(private, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        with public.open('xb') as f:
            f.write(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        print(f'Issuer private key: {private}\nCustomer verification key: {public}')
        return
    if args.validate:
        license = validate_license_key(args.validate)
        print(json.dumps({'valid': license.valid, 'tier': license.tier, 'message': license.message}, indent=2))
        if not license.valid:
            raise SystemExit(1)
        return
    if args.batch:
        customers = json.loads(Path(args.batch).read_text())
    elif args.email:
        customers = [{'tier': args.tier, 'email': args.email, 'days': args.days}]
    else:
        parser.error('--email, --batch, --validate or --init-keys is required')
    for customer in customers:
        token = generate_license_key(customer.get('tier', 'pro'), customer['email'], customer.get('days', 30))
        print(json.dumps({'email': customer['email'], 'license': token}))


if __name__ == '__main__':
    main()
