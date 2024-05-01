import logfire

logfire.install_auto_tracing(modules=["hello"])

from hello import main  # noqa

main()
