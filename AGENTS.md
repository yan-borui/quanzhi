# Repository Guidelines

## Project Structure & Module Organization

The game code lives in `include/`. Core abstractions such as characters, skills, players, and plugin contracts are in `include/core/`; playable roles belong in `include/characters/`; cross-cutting mechanics live in `include/systems/`; and construction and plugin discovery are handled by `include/factory/`. Keep transport and presentation code in `include/server.py`, `include/client.py`, or `include/backend/`, rather than mixing it into game rules. Configuration defaults are stored in `include/config/default_config.json`. Tests are in `tests/` and mirror features rather than package paths. `clientgui.py` is a legacy text-protocol client and is not compatible with the current server.

## Build, Test, and Development Commands

Create and activate a local virtual environment, then run:

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -v
python -m compileall include
cd include; python main.py
```

The first command installs GUI/runtime dependencies. Pytest runs the full suite; `compileall` matches the CI syntax check; `main.py` launches the CLI game. For network play, start `python include/server.py --host 0.0.0.0 --port 50007`, then `python include/client.py --host 127.0.0.1 --port 50007` in another terminal.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation and type annotations for public APIs. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and uppercase constants such as `ROLE_ID` and `STATS_DATA`. Existing comments and docstrings are primarily Chinese; keep new documentation consistent with the surrounding file. Character implementations should inherit `Character` and remain isolated in one descriptively named module. No formatter is configured, so keep imports, line lengths, and spacing aligned with nearby code.

## Testing Guidelines

Tests use pytest. Name files `test_<feature>.py`, classes `Test<Behavior>`, and cases `test_<expected_behavior>`. Add focused regression tests for rule changes, plugin schema/loading behavior, and backend/frontend boundaries. Avoid network or GUI dependencies in unit tests. Run the complete suite before opening a pull request; CI tests Python 3.10 and 3.12.

## Commit & Pull Request Guidelines

History uses short, imperative summaries in English or Chinese, for example `refactor backend status and action handling` or `修改镰刀工逻辑`. Keep each commit scoped to one coherent change. Pull requests should explain player-visible behavior, list validation commands, link relevant issues, and include screenshots for GUI changes. Call out configuration, protocol, or plugin-interface compatibility changes explicitly.

## Configuration & Plugin Safety

Do not commit secrets or machine-specific paths. Preserve the JSON network protocol and validate untrusted plugin metadata through the existing schema and loader. Consult `CHARACTER_GUIDE.md` before adding a role or third-party plugin.
