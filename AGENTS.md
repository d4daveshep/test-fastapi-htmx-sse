# AI Agent Guidelines for test-fastapi-htmx-sse

## Build/Run Commands
- **Run application**: `uv run python main.py`
- **Install dependencies**: `uv add <package>`
- **Sync environment**: `uv sync`
- **Run single test**: `uv run python -m pytest tests/test_specific.py::test_function`
- **Run all tests**: `uv run python -m pytest`

## Code Style Guidelines

### Python Style
- **Python version**: 3.13+ (see .python-version)
- **Package manager**: Use `uv` for dependency management
- **Imports**: Standard library first, third-party, then local imports
- **Formatting**: Follow PEP 8 conventions
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Type hints**: Use type annotations for function parameters and return types
- **Error handling**: Use specific exception types, avoid bare except clauses

### File Organization
- Main application logic in root level Python files
- Keep the simple project structure as established
- Use descriptive function and variable names
- Include docstrings for public functions and classes