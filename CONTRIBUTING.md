# Contributing to DocuMint

Thank you for your interest in contributing to DocuMint! This guide will help you get started.

## Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/MukundaKatta/DocuMint.git
   cd DocuMint
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install development dependencies:**

   ```bash
   make dev
   ```

## Running Tests

```bash
make test
```

For coverage reports:

```bash
make test-cov
```

## Code Style

We use **Black** for formatting and **Ruff** for linting:

```bash
make format
make lint
```

Please ensure all checks pass before submitting a pull request.

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Write tests for any new functionality.
3. Ensure all tests pass and linting is clean.
4. Update documentation if your changes affect the public API.
5. Submit a pull request with a clear description of the changes.

## Reporting Issues

- Use GitHub Issues to report bugs or request features.
- Include a minimal reproducible example when reporting bugs.
- Specify the Python version and OS you are using.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
