# readme-ai-gen

`readme-ai-gen` is a Python CLI that turns a GitHub profile URL or repository URL into a polished `README.md` by combining GitHub API data, deterministic README asset builders, and an LLM backend.

It supports both of these generation modes:

- Profile mode for `username/username` GitHub profile READMEs
- Project mode for standard repository READMEs

## Features

- Auto-detects profile vs project mode from the GitHub URL
- Fetches structured GitHub context before the model runs
- Builds all third-party badge, widget, and image URLs deterministically
- Supports Gemini and OpenAI providers
- Includes interactive setup with `questionary` and `rich`
- Supports `--dry-run`, custom output paths, and clipboard copy
- Ships with unit tests for fetcher, builder, and generator modules

## Installation

### Local development

```bash
git clone https://github.com/lekhan/readme-ai-gen
cd readme-ai-gen
pip install -e .
```

### Environment setup

Create a `.env` file from the example and add at least one LLM key:

```bash
cp .env.example .env
```

Required environment variables:

- `GEMINI_API_KEY` or `OPENAI_API_KEY`
- `GITHUB_TOKEN` is optional, but recommended for higher rate limits and GraphQL pinned-repo support

## Usage

### Interactive mode

```bash
readme-gen https://github.com/mithun50
```

### Profile README

```bash
readme-gen https://github.com/mithun50 \
  --mode profile \
  --color A855F7 \
  --header venom \
  --animation twinkling \
  --font "JetBrains Mono" \
  --stats-theme radical \
  --badge-style for-the-badge \
  --height 200 \
  --sections typing,badges,snake,about,ventures,opensource,tech,stats,contrib_graph,trophies,quote,social,footer \
  --icons py,ts,js,react,fastapi,docker,git,linux,firebase,vscode \
  --llm gemini \
  --output ./README.md
```

### Project README

```bash
readme-gen https://github.com/mithun50/readme-ai-gen \
  --mode project \
  --color 06B6D4
```

### Preview without writing

```bash
readme-gen https://github.com/mithun50/readme-ai-gen --mode project --dry-run
```

## CLI Flags

- `--mode [auto|profile|project]`
- `--color <hex-or-theme>`
- `--header <style>`
- `--animation <name>`
- `--font <font>`
- `--stats-theme <theme>`
- `--badge-style <style>`
- `--height <int>`
- `--sections <csv>`
- `--icons <csv>`
- `--llm [gemini|openai]`
- `--output <path>`
- `--copy`
- `--dry-run`

## Project Layout

```text
readme-ai-gen/
├── readme_ai_gen/
│   ├── __init__.py
│   ├── builder.py
│   ├── cli.py
│   ├── config.py
│   ├── fetcher.py
│   ├── generator.py
│   ├── renderer.py
│   └── utils.py
├── tests/
│   ├── test_builder.py
│   ├── test_fetcher.py
│   └── test_generator.py
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## Architecture

### `fetcher.py`

Collects GitHub REST and GraphQL data asynchronously and returns one unified context dictionary for profile or project generation.

### `builder.py`

Builds all README widget URLs deterministically so the model never has to invent badge or asset links.

### `generator.py`

Constructs the system and user prompts, then calls Gemini or OpenAI to produce the final Markdown.

### `renderer.py`

Coordinates fetcher, builder, and generator into one preparation and render pipeline.

### `cli.py`

Exposes the `readme-gen` command, interactive wizard, progress display, summary panel, and output handling.

## Testing

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

## Notes

- Without `GITHUB_TOKEN`, the tool still works, but pinned repositories and rate limits are more restrictive.
- Interactive mode requires `questionary` to be installed.
- `--dry-run` prevents file writes and clipboard operations by design.

## License

MIT
