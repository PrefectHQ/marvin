# Legacy Documentation

If you want to view documentation of previous versions of Marvin, here's a step by step guide on how to do that.

## Prerequisites

- `Git`
- `python3`
- `pip`

## Automated Script for Legacy Documentation
To build and view the docs for a specific version of Marvin, you can use [this script](https://github.com/PrefectHQ/marvin/blob/main/scripts/serve_legacy_docs).

You can either clone the [Marvin repo](https://github.com/PrefectHQ/marvin.git) and run the script locally, or copy the script and run it directly in your terminal after making it executable:
```bash
# unix
chmod +x scripts/serve_legacy_docs

# run the script (default version is v1.5.6)
./scripts/serve_legacy_docs

# optionally, specify a version
./scripts/serve_legacy_docs v1.5.3
```

## Manual Steps

If you prefer to manually perform the steps or need to tailor them for your specific operating system, follow these instructions:

1. **Clone the Repository**  
   Clone the Marvin repository using Git:
   ```bash
   git clone https://github.com/PrefectHQ/marvin.git
   cd marvin
   ```

2. **Checkout the Specific Tag**  
   Checkout the tag for the version you are interested in. Replace `v1.5.6` with the desired version tag:
   ```bash
   git fetch --tags
   git checkout tags/v1.5.6
   ```

3. **Create a Virtual Environment**  
   Create and activate a virtual environment to isolate the dependency installation:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

4. **Install Dependencies**  
   Install the necessary dependencies for the documentation:
   ```bash
   pip install -e ".[dev,docs]"
   ```

5. **Serve the Documentation Locally**  
   Use `mkdocs` to serve the documentation:
   ```bash
   mkdocs serve
   ```
   This will start a local server. View the documentation by navigating to `http://localhost:8000` in your web browser.

6. **Exit Virtual Environment**  
   Once finished, you can exit the virtual environment:
   ```bash
   deactivate
   ```

   Optionally, you can remove the virtual environment folder:
   ```bash
   rm -rf venv
   ```