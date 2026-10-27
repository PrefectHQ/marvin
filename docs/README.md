# Marvin documentation

Published at [askmarvin.ai](https://askmarvin.ai). Navigation and site settings are in `docs.json`.

From this directory, preview the site with the Mintlify CLI:

```bash
npx mint dev
```

Handwritten `.mdx` pages explain usage. `api-reference/` is generated from Python signatures and docstrings; edit the source rather than those pages.

From the repository root:

```bash
uv run scripts/create_mintlify_api_ref.py
```

Use complete, runnable examples. Describe what the library does separately from what a model might decide or generate. Link to an existing page instead of duplicating its instructions.
