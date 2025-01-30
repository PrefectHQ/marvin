#!/bin/bash
if ! command -v goose &> /dev/null
then
    # ask the user if its ok to install it
    read -p "goose (block.github.io/goose) is not installed. Would you like to install it? (y/n) " answer
    if [ "$answer" = "y" ]
    then
        curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash
    fi
fi

goose session --with-extension 'uv run examples/you_have_been_goosed/goose_em.py'