"""
Provide an invisible option that can be used to add parameters to a command function.

This should probably not be used outside of `typerdrive`.
"""
import typer

CloakingDevice = typer.Option(parser=lambda _: _, hidden=True, expose_value=False, default_factory=lambda: None)
