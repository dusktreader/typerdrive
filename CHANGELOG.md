# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## v0.5.2 - 2025-05-12
- Fixed error when showing settings where none are set (have defaults)


## v0.5.1 - 2025-05-12
- Added `log_errors` utility function


## v0.5.0 - 2025-05-10
- Accidentally bumped minor version instead of patch


## v0.4.2 - 2025-05-10
- Fixed `app_name`


## v0.4.1 - 2025-05-09
- Fixed missing loguru dependency


## v0.4.0 - 2025-05-09
- Added `@attach_logging()` decorator and logs subcommands
- Added TyperdriveConfig to control global configuration for typerdrive specifically
- Moved `app_name` to `TyperdriveConfig`
- Added logging configuration controls to `TyperdriveConfig`
- Added a `publish` makefile target
- Fixed imports in `__all__` for root `__init__.py`
- Moved directory helpers to `dirs.py`
- Updated demos, examples, documentation, and tests


## v0.3.0 - 2025-05-08
- Added `@attach_client` and `TyperdriveClient`


## v0.2.0 - 2025-05-04
- Enabled access to settings and cache through command function parameters


## v0.1.0 - 2025-05-02
- Forked from typer-repyt and released as new package.
