import base64
import hashlib
import hmac
import os
import re
import subprocess
import sys
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from loguru import logger
from typer.testing import CliRunner
from typerdrive.config import set_typerdrive_config


# Test-only stand-in for age scrypt passphrase encryption (real scrypt takes ~1.5s per call).
# Mimics the envelope shape that production validates; not secure.
def _test_fake_passphrase_encrypt(plaintext: bytes, passphrase: str) -> bytes:
    if len(plaintext) > 74:
        raise ValueError("Test fake only supports payloads up to 74 bytes")
    salt = os.urandom(16)
    nonce = os.urandom(16)
    key = hashlib.sha256(b"typerdrive test fake\0" + passphrase.encode("utf-8") + salt).digest()
    stanza_body = len(plaintext).to_bytes(2, "big") + hashlib.sha256(b"stanza" + key).digest()[:30]
    stanza = (
        b"age-encryption.org/v1\n-> scrypt "
        + base64.b64encode(salt).rstrip(b"=")
        + b" 1\n"
        + base64.b64encode(stanza_body).rstrip(b"=")
        + b"\n"
    )
    padded = plaintext.ljust(74, b"\0")
    stream = b"".join(hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest() for counter in range(3))
    encrypted = bytes(left ^ right for left, right in zip(padded, stream, strict=False))
    payload = nonce + encrypted + hmac.digest(key, b"payload" + nonce + encrypted, "sha256")[:16]
    footer_input = stanza + b"--- \n" + payload
    wrapped = (
        stanza + b"--- " + base64.b64encode(hmac.digest(key, footer_input, "sha256")).rstrip(b"=") + b"\n" + payload
    )
    return wrapped


def _test_fake_passphrase_decrypt(ciphertext: bytes, passphrase: str) -> bytes:
    import pyrage

    age: Any = pyrage
    try:
        wrapped = ciphertext
        match = re.fullmatch(
            rb"age-encryption.org/v1\n-> scrypt ([A-Za-z0-9+/]{22}) 1\n"
            rb"([A-Za-z0-9+/]{43})\n--- ([A-Za-z0-9+/]{43})\n(.{106})",
            wrapped,
            re.DOTALL,
        )
        if match is None:
            raise ValueError
        salt = base64.b64decode(match.group(1) + b"==")
        stanza_body = base64.b64decode(match.group(2) + b"=")
        mac = base64.b64decode(match.group(3) + b"=")
        payload = match.group(4)
        nonce, encrypted, tag = payload[:16], payload[16:90], payload[90:]
        key = hashlib.sha256(b"typerdrive test fake\0" + passphrase.encode("utf-8") + salt).digest()
        footer_input = wrapped[: wrapped.index(b"--- ")] + b"--- \n" + payload
        expected_mac = hmac.digest(key, footer_input, "sha256")
        expected_body = len(stanza_body[:2]).to_bytes(2, "big") + hashlib.sha256(b"stanza" + key).digest()[:30]
        expected_tag = hmac.digest(key, b"payload" + nonce + encrypted, "sha256")[:16]
        if (
            not hmac.compare_digest(mac, expected_mac)
            or not hmac.compare_digest(stanza_body[2:], expected_body[2:])
            or not hmac.compare_digest(tag, expected_tag)
        ):
            raise ValueError
        length = int.from_bytes(stanza_body[:2], "big")
        if length > 74:
            raise ValueError
        stream = b"".join(hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest() for counter in range(3))
        padded = bytes(left ^ right for left, right in zip(encrypted, stream, strict=False))
        return padded[:length]
    except (ValueError, TypeError, IndexError) as exc:
        raise age.DecryptError() from exc


@pytest.fixture(autouse=True)
def _test_fake_pyrage_passphrase(monkeypatch: pytest.MonkeyPatch) -> None:
    try:
        import pyrage
    except ModuleNotFoundError as exc:
        if exc.name != "pyrage":
            raise
        return
    age: Any = pyrage
    monkeypatch.setattr(age.passphrase, "encrypt", _test_fake_passphrase_encrypt)
    monkeypatch.setattr(age.passphrase, "decrypt", _test_fake_passphrase_decrypt)


@pytest.fixture
def run_without_pyrage() -> Callable[[str], subprocess.CompletedProcess[str]]:
    def run(source: str) -> subprocess.CompletedProcess[str]:
        root = Path(__file__).resolve().parent.parent
        pythonpath = str(root / "src")
        if os.environ.get("PYTHONPATH"):
            pythonpath = os.pathsep.join((pythonpath, os.environ["PYTHONPATH"]))
        script = f"""\
import importlib.abc
import sys

class MissingPyrage(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pyrage":
            raise ModuleNotFoundError("No module named 'pyrage'", name="pyrage")

sys.meta_path.insert(0, MissingPyrage())
{source}
"""
        return subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=root,
            env={**os.environ, "PYTHONPATH": pythonpath},
        )

    return run


@pytest.fixture(scope="session", autouse=True)
def _():
    set_typerdrive_config(
        app_name="test",
        console_width=80,
    )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture) -> Generator[pytest.LogCaptureFixture, None, None]:
    logger.enable("typerdrive")
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)
