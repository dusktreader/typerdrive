from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, BeforeValidator

from typerdrive.client.base import ClientLogFunc, TyperdriveClient
from typerdrive.client.exceptions import ClientError


def pyright_safe_validator(value: str) -> str:
    AnyHttpUrl(value)
    return value


class ClientSpec(BaseModel):
    base_url: Annotated[str, BeforeValidator(pyright_safe_validator)]
    log_func: ClientLogFunc | None = None


class ClientManager:

    clients: dict[str, TyperdriveClient]

    def __init__(self):
        self.clients = {}

    def add_client(self, name: str, spec: ClientSpec) -> None:
        ClientError.require_condition(
            name not in self.clients,
            f"Client with name {name} already exists in context",
        )
        self.clients[name] = TyperdriveClient(log_func=spec.log_func, base_url=str(spec.base_url))

    def get_client(self, name: str) -> TyperdriveClient:
        return ClientError.enforce_defined(self.clients.get(name), f"No client named {name} found in context")
