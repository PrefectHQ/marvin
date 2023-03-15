from setuptools import find_packages, setup

required_deps = open("requirements.txt").read().strip().split("\n")
dev_deps = open("requirements-dev.txt").read().strip().split("\n")

setup(
    # Package metadata
    name="marvin",
    url="https://github.com/PrefectHQ/marvin",
    version="0.3",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    # Package setup
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    entry_points={
        "console_scripts": ["marvin=marvin.cli.cli:app"],
    },
    # Requirements
    python_requires=">=3.10",
    install_requires=required_deps,
    extras_require={
        "dev": required_deps + dev_deps,
    },
)
