import pytest
from pydantic import ValidationError
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError
from typerdrive.client.manager import ClientManager, ClientSpec


class TestClientSpec:
    def test_accepts_valid_url(self):
        ClientSpec(base_url="https://the.force.io")

    def test_raises_error_on_invalid_url(self):
        with pytest.raises(ValidationError, match="Input should be a valid URL"):
            ClientSpec(base_url="not-a-url")


class TestClientManager:
    def test_inti__initializes_client_dict(self):
        manager = ClientManager()
        assert manager.clients == {}

    def test_add_client__adds_a_client(self):
        manager = ClientManager()
        spec = ClientSpec(base_url="https://the.force.io")
        manager.add_client("test", spec)
        assert len(manager.clients) == 1
        client = manager.clients["test"]
        assert str(client.base_url) == "https://the.force.io"

    def test_add_client__raises_error_if_client_already_exists(self):
        manager = ClientManager()
        manager.clients["test"] = TyperdriveClient()
        with pytest.raises(ClientError, match="Client with name test already exists in context"):
            manager.add_client("test", ClientSpec(base_url="https://the.force.io"))

    def test_get_client__fetches_a_client_by_name(self):
        manager = ClientManager()
        manager.clients["test"] = TyperdriveClient(base_url="https://the.force.io")
        client = manager.get_client("test")
        assert client.base_url == "https://the.force.io"

    def test_get_client__raises_an_error_if_the_client_does_not_exist(self):
        manager = ClientManager()
        with pytest.raises(ClientError, match="No client named test found in context"):
            manager.get_client("test")
