# Contributing

Thank you for your interest in improving `cargo-dispatch`.

## Workflow

1. Open an [issue](https://github.com/nursich/cargo-dispatch/issues) describing the bug or
   feature (use the templates).
2. Create a branch from `main`: `feature/<short-name>` or `fix/<short-name>`.
3. Make small, focused commits. Commit messages follow
   [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `ci: ...`, `refactor: ...`.
4. Before pushing, run locally:
   ```bash
   ruff format . && ruff check . && mypy && pytest --cov
   ```
5. Open a pull request, link the issue (`Closes #12`) and wait for CI to pass.
   `main` is protected: changes are merged only through green pull requests.

## Code style

- Type hints on all public functions; docstrings in Google style.
- New behaviour comes with tests; coverage must stay at or above 90 %.
- Keep results reproducible: random experiments take an explicit seed.
