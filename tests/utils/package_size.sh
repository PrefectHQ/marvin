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

# Create a temporary directory
TMPDIR=$(mktemp -d)

# Navigate to the temporary directory and create a new venv
cd $TMPDIR
python3 -m venv venv
source venv/bin/activate

# If an additional package was specified, install it
if [ -n "$ADD_PACKAGE" ]; then
  pip install $ADD_PACKAGE
fi

# Install the package in the new venv
pip install $OLDPWD

# Calculate the size of the installed package
echo "Size of the installed package and its dependencies:"
du -sh $VIRTUAL_ENV

# If an additional package was installed, uninstall it
if [ -n "$ADD_PACKAGE" ]; then
  pip uninstall -y $(basename $ADD_PACKAGE)
fi

# Deactivate and remove the virtual environment
deactivate
cd $OLDPWD
rm -rf $TMPDIR
