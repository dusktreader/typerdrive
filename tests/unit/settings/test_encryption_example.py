import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from typer.testing import CliRunner
from typerdrive import EncryptedSecretStr
from typerdrive.config import get_typerdrive_config
from typerdrive.settings.secrets import encryption as encryption_module
from typerdrive.settings.secrets.encryption import SecretEncryption

pytest.importorskip("pyrage")


@pytest.fixture
def example() -> ModuleType:
    path = Path(__file__).resolve().parents[3] / "examples/settings/encrypted_secrets.py"
    spec = importlib.util.spec_from_file_location("encrypted_secrets_example", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    original = get_typerdrive_config()
    spec.loader.exec_module(module)
    assert get_typerdrive_config() == original
    module.configure()
    return module


def test_encrypted_example_lifecycle(example: ModuleType, runner: CliRunner, mocker):
    assert example.AppSettings.model_fields["api_token"].annotation is EncryptedSecretStr
    passphrase = "example-private-passphrase"
    new_passphrase = "example-new-passphrase"
    token = "example-private-token"
    encryption = SecretEncryption(get_typerdrive_config())
    prompt = mocker.spy(encryption_module.typer, "prompt")

    def invoke(*args: str, inputs: str = ""):
        result = runner.invoke(example.cli, list(args), input=inputs)
        assert token not in result.output
        assert passphrase not in result.output
        assert new_passphrase not in result.output
        assert result.exit_code == 0, result.output
        return result

    setup = invoke("settings", "encryption", "setup", inputs=f"{passphrase}\n{passphrase}\n")
    assert "New passphrase" in setup.output
    assert encryption.material_path.exists()
    saved = invoke("set-token", inputs=f"{token}\n{passphrase}\n")
    assert "API token" in saved.output and "saved encrypted" in saved.output
    assert not any(call.args[0] == "Secret encryption passphrase" for call in prompt.call_args_list)
    settings_text = get_typerdrive_config().settings_path.read_text()
    assert token not in settings_text
    assert passphrase not in settings_text
    ciphertext = json.loads(settings_text)["api_token"]
    assert ciphertext.startswith("age:")
    assert not encryption.cache_path.exists()

    prompt_count = prompt.call_count
    shown = invoke("settings", "show")
    assert "**********" in shown.output
    assert passphrase not in shown.output
    used = invoke("use-token", inputs=f"{passphrase}\n")
    assert "API token is ready to use." in used.output
    assert encryption.cache_path.exists()
    assert encryption.decrypt(ciphertext) == token
    prompt_count = prompt.call_count
    cached = invoke("use-token")
    assert prompt.call_count == prompt_count
    assert "passphrase" not in cached.output.lower()
    assert "API token is ready to use." in cached.output

    invoke("settings", "encryption", "lock")
    assert not encryption.cache_path.exists()
    after_lock = invoke("use-token", inputs=f"{passphrase}\n")
    assert "Secret encryption passphrase" in after_lock.output
    assert prompt.call_count == prompt_count + 1
    assert encryption.cache_path.exists()
    invoke("settings", "encryption", "unlock", inputs=f"{passphrase}\n")
    assert encryption.cache_path.exists()
    invoke("settings", "encryption", "change-passphrase", inputs=f"{passphrase}\n{new_passphrase}\n{new_passphrase}\n")
    assert json.loads(get_typerdrive_config().settings_path.read_text())["api_token"] == ciphertext
    assert not encryption.cache_path.exists()
    rotation_prompt_count = prompt.call_count
    used_again = invoke("use-token", inputs=f"{new_passphrase}\n")
    assert "Secret encryption passphrase" in used_again.output
    assert prompt.call_count == rotation_prompt_count + 1
    assert encryption.cache_path.exists()
    assert "API token is ready to use." in used_again.output
