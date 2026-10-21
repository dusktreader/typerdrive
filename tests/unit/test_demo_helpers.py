from io import StringIO
from pathlib import Path

from pytest_mock import MockerFixture
from rich.console import Console

from typerdrive.config import get_typerdrive_config, set_typerdrive_config
from typerdrive_demo.attach_database import (
    demo_1__attach_database__async_sql,
    demo_2__attach_database__sync_wrappers,
    demo_3__attach_database__context_lookup,
)
from typerdrive_demo.config_commands import demo_01__show_app_info, demo_02__show_app_version, demo_03__show_full_config
from typerdrive_demo.helpers import capture, run_demo


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


def test_database_demos_use_isolated_migration_state(tmp_path: Path):
    original_config = get_typerdrive_config()
    set_typerdrive_config(app_name="database-demo-test", state_home=tmp_path, cache_home=tmp_path / ".cache")
    try:
        for demo in (
            demo_1__attach_database__async_sql,
            demo_2__attach_database__sync_wrappers,
            demo_3__attach_database__context_lookup,
        ):
            result = capture(demo)
            assert result.error is None
            assert result.exit_code == 0
    finally:
        set_typerdrive_config(**original_config.model_dump())
