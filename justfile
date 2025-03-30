# Check for uv installation
check-uv:
    #!/usr/bin/env sh
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv is not installed or not found in expected locations."
        case "$(uname)" in
            "Darwin")
                echo "To install uv on macOS, run one of:"
                echo "• brew install uv"
                echo "• curl -LsSf https://astral.sh/uv/install.sh | sh"
                ;;
            "Linux")
                echo "To install uv, run:"
                echo "• curl -LsSf https://astral.sh/uv/install.sh | sh"
                ;;
            *)
                echo "To install uv, visit: https://github.com/astral-sh/uv"
                ;;
        esac
        exit 1
    fi

# Build and serve documentation
serve-docs: check-uv
    cd docs && uv run mintlify dev

# Install development dependencies
install: check-uv
    uv sync

# Clean up environment
clean: check-uv
    deactivate || true
    rm -rf .venv

run-pre-commits: check-uv
    uv run pre-commit run --all-files

run-slackbot: check-uv
    uv run --extra slackbot examples/slackbot/start.py