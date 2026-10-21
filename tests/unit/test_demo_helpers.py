from io import StringIO

from pytest_mock import MockerFixture
from rich.console import Console

from typerdrive.config import get_typerdrive_config
from typerdrive_demo.config_commands import demo_01__show_app_info, demo_02__show_app_version, demo_03__show_full_config
from typerdrive_demo.helpers import run_demo


def test_run_demo_restores_typerdrive_config(mocker: MockerFixture):
    original_config = get_typerdrive_config()
    output = StringIO()
    console = Console(file=output, width=140)
    mocker.patch("typerdrive_demo.helpers.Confirm.ask", return_value=False)

    for demo in (demo_01__show_app_info, demo_02__show_app_version, demo_03__show_full_config):
        assert run_demo(demo, console) is False
        assert get_typerdrive_config().model_dump() == original_config.model_dump()

    assert "config-demo v1.2.3" in output.getvalue()
    assert "config-demo-state" in output.getvalue()
    assert "config-demo-cache" in output.getvalue()
