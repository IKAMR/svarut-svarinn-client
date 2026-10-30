"""Maskinporten JWT grant with RSA/RS256; credentials and token stay in memory."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from uuid import uuid4

from .config import SvarUtSetup
from .network import ApiError, HttpsTransport, test_base


@dataclass(frozen=True, repr=False)
class SessionSecrets:
    integration_password: str = field(default='', repr=False)
    signing_key_password: str = field(default='', repr=False)
    svarinn_password: str = field(default='', repr=False)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def _local_file(value: str) -> bytes:
    try:
        path = Path(value).expanduser()
        if not value or not path.is_absolute() or not path.is_file():
            raise ValueError
        with path.open('rb') as stream:
            data = stream.read(1024 * 1024 + 1)
        if not data or len(data) > 1024 * 1024:
            raise ValueError
        return data
    except (OSError, ValueError):
        raise ApiError("Kan ikke lese nøkkel-/sertifikatfil. Velg en absolutt filsti til en lokal fil under 1 MiB.") from None


def make_assertion(setup: SvarUtSetup, password: str, *, now: int | None = None) -> str:
    """No private RSA math: all key validation/signing is delegated to cryptography."""
    issuer = test_base(setup.maskinporten_base_url, maskinporten=True)
    if not setup.maskinporten_client_id:
        raise ApiError("Maskinporten klient-ID mangler.")
    try:
        from cryptography import x509
        from cryptography.exceptions import UnsupportedAlgorithm
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.hazmat.primitives.serialization import pkcs12
    except ImportError:
        raise ApiError("Kryptografibiblioteket mangler. Kjør install.bat på nytt.") from None
    data = _local_file(setup.signing_key_file)
    pwd = password.encode('utf-8') if password else None
    certificates = []
    try:
        suffix = Path(setup.signing_key_file).suffix.lower()
        if suffix in ('.p12', '.pfx'):
            key, cert, extra = pkcs12.load_key_and_certificates(data, pwd)
            certificates = ([cert] if cert else []) + list(extra or [])
        elif suffix == '.jwk':
            jwk = json.loads(data)
            if jwk.get('kty') != 'RSA' or jwk.get('alg', 'RS256') != 'RS256' or 'oth' in jwk:
                raise ValueError
            def integer(name):
                encoded = jwk[name]
                if not isinstance(encoded, str) or len(encoded) > 4096:
                    raise ValueError
                return int.from_bytes(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)), 'big')
            key = rsa.RSAPrivateNumbers(integer('p'), integer('q'), integer('d'),
                       integer('dp'), integer('dq'), integer('qi'),
                       rsa.RSAPublicNumbers(integer('e'), integer('n'))).private_key()
            if not setup.maskinporten_key_id:
                raise ApiError("JWK krever at registrert kid fylles inn i Oppsett.")
        else:
            key = serialization.load_pem_private_key(data, password=pwd)
            if b'-----BEGIN CERTIFICATE-----' in data:
                certificates = x509.load_pem_x509_certificates(data)
        if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
            raise ApiError("Maskinporten-testen krever en privat RSA-nøkkel på minst 2048 bit.")
        header = {'alg': 'RS256'}
        if setup.maskinporten_key_id:
            header['kid'] = setup.maskinporten_key_id
        else:
            if setup.signing_certificate_file:
                cert_data = _local_file(setup.signing_certificate_file)
                certificates = (x509.load_pem_x509_certificates(cert_data)
                                if b'-----BEGIN CERTIFICATE-----' in cert_data
                                else [x509.load_der_x509_certificate(cert_data)])
            matching = [c for c in certificates if c.public_key().public_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo) ==
                key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)]
            if len(matching) != 1:
                raise ApiError("Velg registrert kid, eller sertifikat med offentlig nøkkel som passer til privatnøkkelen.")
            # Leaf first; append issuer certificates from the supplied chain.
            ordered = [matching[0]]
            remaining = [c for c in certificates if c != matching[0]]
            while remaining and ordered[-1].issuer != ordered[-1].subject:
                parent = next((c for c in remaining if c.subject == ordered[-1].issuer), None)
                if parent is None:
                    break
                ordered.append(parent)
                remaining.remove(parent)
            header['x5c'] = [base64.b64encode(c.public_bytes(serialization.Encoding.DER)).decode('ascii') for c in ordered]
        stamp = int(time.time()) if now is None else now
        claims = {'aud': issuer, 'iss': setup.maskinporten_client_id, 'scope': 'ks:fiks',
                  'iat': stamp, 'exp': stamp + 120, 'jti': str(uuid4())}
        compact = lambda x: json.dumps(x, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        signed = (_b64(compact(header)) + '.' + _b64(compact(claims))).encode('ascii')
        signature = key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
        return signed.decode('ascii') + '.' + _b64(signature)
    except ApiError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, UnsupportedAlgorithm):
        raise ApiError("Nøkkelen kunne ikke brukes. Kontroller filformat, nøkkelpassord og sertifikat/kid. Private verdier er ikke logget.") from None


class MaskinportenClient:
    def __init__(self, transport: HttpsTransport):
        self.transport = transport
        self.clear()

    def clear(self) -> None:
        self._token = ''
        self._expires_at = 0.0
        self._binding = b''

    def token(self, setup: SvarUtSetup, secrets: SessionSecrets, *, fresh: bool = False) -> str:
        base = test_base(setup.maskinporten_base_url, maskinporten=True)
        # Changes to the configured key or key password invalidate a cached token.
        try:
            stamps = [(p, Path(p).stat().st_mtime_ns, Path(p).stat().st_size)
                      for p in (setup.signing_key_file, setup.signing_certificate_file) if p]
        except OSError:
            self.clear()
            raise ApiError("Konfigurert nøkkel-/sertifikatfil kan ikke leses.") from None
        binding = hashlib.sha256(json.dumps([vars(setup), stamps, secrets.signing_key_password], sort_keys=True).encode()).digest()
        if not fresh and binding == self._binding and self._token and time.monotonic() + 30 < self._expires_at:
            return self._token
        self.clear()
        assertion = make_assertion(setup, secrets.signing_key_password)
        response = self.transport.request('POST', base + 'token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            body=urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion}).encode('ascii'))
        if not isinstance(response, dict):
            raise ApiError("Uventet tokensvar fra Maskinporten.")
        value, expiry = response.get('access_token'), response.get('expires_in')
        if (not isinstance(value, str) or not value or len(value) > 65536 or
            any(ord(c) < 33 or ord(c) > 126 for c in value) or
            type(expiry) is not int or not 0 < expiry <= 86400 or
            str(response.get('token_type', '')).lower() != 'bearer'):
            raise ApiError("Maskinporten returnerte et ufullstendig tokensvar.")
        self._token, self._binding = value, binding
        self._expires_at = time.monotonic() + expiry
        return self._token
