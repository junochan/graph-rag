# Contributing to Graph RAG

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Fork and clone** the repository

2. **Install dependencies**

```bash
uv sync --dev
```

3. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your local settings
```

4. **Start infrastructure**

```bash
docker run -d --name nebula -p 9669:9669 -p 19669:19669 vesoft/nebula-graph:v3.6.0
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

5. **Initialize and run**

```bash
uv run python scripts/init_graph.py
uv run python main.py
```

## Code Style

- **Python**: We use [ruff](https://github.com/astral-sh/ruff) for linting and [black](https://github.com/psf/black) for formatting
- **TypeScript**: We use ESLint with the Next.js config
- Line length limit: 100 characters

Run checks locally:

```bash
# Python linting & formatting
uv run ruff check src/
uv run black --check src/

# Type checking
uv run mypy src/

# Tests
uv run pytest
```

## Making Changes

1. Create a new branch from `main`:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and ensure:
   - All existing tests pass
   - New code has appropriate tests
   - Code follows the project style guidelines
   - Commit messages are clear and descriptive

3. Push your branch and open a Pull Request

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include a clear description of what changed and why
- Update documentation if your change affects user-facing behavior
- Add an entry to `CHANGELOG.md` under the `[Unreleased]` section

## Reporting Issues

When reporting bugs, please include:

- Steps to reproduce the issue
- Expected vs actual behavior
- Python version and OS
- Relevant logs or error messages

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
