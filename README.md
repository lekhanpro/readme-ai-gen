<div align="center">

# readme-ai-gen

**AI-powered GitHub README generator with live preview studio**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-readme--ai--gen.vercel.app-8b5cf6?style=for-the-badge&logo=vercel&logoColor=white)](https://readme-ai-gen.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-lekhanpro%2Freadme--ai--gen-181717?style=for-the-badge&logo=github)](https://github.com/lekhanpro/readme-ai-gen)
[![License](https://img.shields.io/badge/License-MIT-06b6d4?style=for-the-badge)](LICENSE)

<br />

Paste a GitHub profile or repository URL, choose your visual direction, and generate a polished README in seconds — powered by NVIDIA, Groq, Gemini, or OpenAI.

<br />

</div>

## About

**readme-ai-gen** is a full-stack README generation studio that combines GitHub API data, deterministic asset builders, and LLM backends to produce production-ready READMEs.

It ships as both a **web studio** (deployed on Vercel) and a **Python CLI** — use whichever fits your workflow.

**Live at** [readme-ai-gen.vercel.app](https://readme-ai-gen.vercel.app)

### Key capabilities

- **Auto-detects** profile vs project mode from the GitHub URL
- **4 LLM providers** — NVIDIA, Groq, Gemini, OpenAI
- **3 content presets** — Minimal, Showcase, Full
- **Live preview** — toggle between markdown source and rendered output
- **Full customization** — accent colors, header styles, animations, fonts, badge styles, stats themes, section toggles
- **Deterministic assets** — all badge, widget, and image URLs are built without LLM hallucination
- **Copy & download** — grab the markdown or save as `README.md` directly

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Vanilla HTML/CSS/JS, Inter + JetBrains Mono, dark glassmorphism UI |
| Backend | Python 3.10+, async/await, httpx, Vercel serverless functions |
| LLM | NVIDIA NIM, Groq, Google Gemini, OpenAI |
| Deploy | [Vercel](https://readme-ai-gen.vercel.app) |

## Getting Started

### Prerequisites

- Python 3.10+
- At least one LLM API key (NVIDIA, Groq, Gemini, or OpenAI)
- `GITHUB_TOKEN` (optional, recommended for higher rate limits)

### Installation

```bash
git clone https://github.com/lekhanpro/readme-ai-gen.git
cd readme-ai-gen
pip install -e .
```

### Environment setup

```bash
cp .env.example .env
```

Add your API keys to `.env`:

```
NVIDIA_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
OPENAI_API_KEY=...
GITHUB_TOKEN=...
```

## Usage

### Web Studio

Visit [readme-ai-gen.vercel.app](https://readme-ai-gen.vercel.app) — no setup required.

### CLI

```bash
# Interactive mode
readme-gen https://github.com/lekhanpro

# Profile README with full options
readme-gen https://github.com/lekhanpro \
  --mode profile \
  --color A855F7 \
  --header venom \
  --animation twinkling \
  --font "JetBrains Mono" \
  --stats-theme radical \
  --badge-style for-the-badge \
  --height 200 \
  --sections typing,badges,snake,about,ventures,opensource,tech,stats,contrib_graph,trophies,quote,social \
  --icons py,ts,js,react,fastapi,docker,git,linux \
  --llm gemini \
  --output ./README.md

# Project README
readme-gen https://github.com/lekhanpro/readme-ai-gen \
  --mode project \
  --color 06B6D4

# Dry run (preview only)
readme-gen https://github.com/lekhanpro/readme-ai-gen --mode project --dry-run
```

### CLI Flags

| Flag | Values |
|------|--------|
| `--mode` | `auto`, `profile`, `project` |
| `--color` | Hex color (e.g. `A855F7`) |
| `--header` | `venom`, `waving`, `soft`, `rect`, `cylinder`, `slice`, `shark`, `egg` |
| `--animation` | `twinkling`, `fadeIn`, `scaleIn`, `blink`, `blinking` |
| `--font` | `JetBrains Mono`, `Fira Code`, `Orbitron`, `Space Mono`, etc. |
| `--stats-theme` | `radical`, `tokyonight`, `dracula`, `midnight-purple`, `synthwave`, `github_dark` |
| `--badge-style` | `for-the-badge`, `flat-square`, `flat`, `plastic` |
| `--sections` | Comma-separated section names |
| `--icons` | Comma-separated tech icon slugs |
| `--llm` | `nvidia`, `groq`, `gemini`, `openai` |
| `--output` | Output file path |
| `--copy` | Copy to clipboard |
| `--dry-run` | Preview without writing |

## Project Structure

```
readme-ai-gen/
├── index.html              # Web studio (single page)
├── app.js                  # Client-side logic
├── styles.css              # Dark glassmorphism theme
├── api/
│   └── generate.py         # Vercel serverless endpoint
├── readme_ai_gen/          # Python package
│   ├── builder.py          # Deterministic asset URL builder
│   ├── cli.py              # CLI interface
│   ├── config.py           # Constants & configuration
│   ├── fetcher.py          # GitHub API data fetcher
│   ├── generator.py        # LLM prompt & generation
│   ├── renderer.py         # Orchestrates fetch → build → generate
│   ├── fallback.py         # Fallback generator
│   └── utils.py            # Utilities
├── tests/                  # Unit tests
├── vercel.json             # Vercel deployment config
├── pyproject.toml          # Python project metadata
└── .env.example            # Environment template
```

## Testing

```bash
python -m unittest discover -s tests -v
```

## License

[MIT](LICENSE)

---

<div align="center">

Built by [@lekhanpro](https://github.com/lekhanpro)

</div>
