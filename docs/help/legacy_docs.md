# Viewing legacy documentation

### Prerequisites

- Git
- Python
- pip

### Steps

1. **Clone the Repository**  
   Clone the 1.5.6 branch of the repository using Git:
   ```bash
   git clone -b 1.5.6 https://github.com/PrefectHQ/marvin.git
   ```

2. **Install Documentation Dependencies**  
   Navigate to the cloned repository and install the required dependencies for building the documentation:
   ```bash
   cd your-repository
   pip install -e ".[dev,docs]"
   ```

3. **Serve the Documentation Locally**  
   Use `mkdocs` to serve the documentation:
   ```bash
   mkdocs serve
   ```
   This will start a local server. You can view the documentation by navigating to `http://127.0.0.1:8000` in your web browser.

## Automated Script for Legacy Documentation
To build and view the docs for a specific version of Marvin, you can use [this script](/scripts/serve_legacy_docs).

You can either clone this repository and run the script locally, or run the script directly from GitHub using `curl`:
```bash
curl -s https://raw.githubusercontent.com/PrefectHQ/marvin/main/scripts/serve_legacy_docs | bash -s -- 1.5.6
```