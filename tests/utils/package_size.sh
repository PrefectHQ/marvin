#!/bin/bash

# Set the default package name
PACKAGE_NAME=marvin

# Set a default additional package to empty
ADD_PACKAGE=""

# Parse the command line arguments
while getopts "a:" opt; do
  case ${opt} in
    a )
      ADD_PACKAGE=$OPTARG
      ;;
    \? )
      echo "Invalid option: $OPTARG" 1>&2
      exit 1
      ;;
    : )
      echo "Invalid option: $OPTARG requires an argument" 1>&2
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

# Build the package with Poetry
poetry build

# Create a temporary directory
TMPDIR=$(mktemp -d)

# Navigate to the temporary directory and create a new Poetry project
cd $TMPDIR
poetry init --no-interaction

# If an additional package was specified, install it
if [ -n "$ADD_PACKAGE" ]; then
  poetry add $ADD_PACKAGE
fi

# Install the package in the new project
poetry add $OLDPWD/dist/${PACKAGE_NAME}*.whl

# Calculate the size of the installed package
echo "Size of the installed package and its dependencies:"
du -sh $(poetry env info -p)

# If an additional package was installed, remove it
if [ -n "$ADD_PACKAGE" ]; then
  poetry remove $(basename $ADD_PACKAGE)
fi

# Remove the temporary directory
cd $OLDPWD
rm -rf $TMPDIR
