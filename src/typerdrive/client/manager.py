"""
Provide a class for managing the `typerdrive` client feature.
"""

from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, BeforeValidator

from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError


def pyright_safe_validator(value: str) -> str:
    AnyHttpUrl(value)
    return value


class ClientSpec(BaseModel):
    base_url: Annotated[str, BeforeValidator(pyright_safe_validator)]


class ClientManager:
    """
    Manage instances of `TyperdriveClient`.
    """

    clients: dict[str, TyperdriveClient]
    """ The `TyperdriveClient instances to manage. """

    def __init__(self):
        self.clients = {}

    def add_client(self, name: str, spec: ClientSpec) -> None:
        """
        Add a `TyperdriveClient` under the given name.

        Parameters:
            name: The name of the client
            spec: A `ClientSpec` describing the client. Used to validate the specs.
        """
        ClientError.require_condition(
            name not in self.clients,
            f"Client with name {name} already exists in context",
        )
        self.clients[name] = TyperdriveClient(base_url=str(spec.base_url))

    def get_client(self, name: str) -> TyperdriveClient:
        """
        Fetch a client from the manager matching the given name.
        """
        return ClientError.enforce_defined(self.clients.get(name), f"No client named {name} found in context")
