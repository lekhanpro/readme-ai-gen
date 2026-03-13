"""LLM prompt construction and provider integrations for readme-ai-gen."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .config import DEFAULT_GEMINI_MODEL, DEFAULT_OPENAI_MODEL
from .fallback import render_fallback_readme
from .utils import DependencyError, LLMError, safe_excerpt, strip_markdown_fences

SYSTEM_PROMPT_TEMPLATE = """
You are a professional README engineer. You generate complete, 
premium-quality README.md files for GitHub.

ABSOLUTE RULES — never break these:
1. Zero mentions of AI, automation, or readme-ai-gen in output.
2. Zero placeholder text. Every value must be real data.
3. Zero watermarks. The README belongs to the developer entirely.
4. Output raw Markdown only. No explanations. No preamble.
5. Never invent data not present in the context provided.
6. Render ONLY the sections listed in the SECTIONS config.
7. All image and badge URLs are pre-built. Use them exactly as given.
   Do not modify, reconstruct, or regenerate any URL.
8. Never line-wrap image/badge URLs. Each URL must be on one line.
9. Wrap header + typing + badges in <div align="center">...</div>.
10. Use HTML <table> for multi-column layouts (about, stats, ventures).
    Add style="border:none" on all <td> elements.
11. Use --- (three dashes) as section dividers.
12. Use # for main sections. Use bold (**text**) for sub-labels.
13. Emojis only in section headings. Max one emoji per heading.
14. Snake setup instructions go in an HTML comment only — not visible.
15. Output length: {output_length} lines.
16. Tone: {tone}
""".strip()

SECTION_INSTRUCTIONS = {
    "header": """### header
- Use CAPSULE HEADER URL above as a Markdown image
- Wrap in <div align=\"center\">
- Use display_name for profile, repo name for project""",
    "typing": """### typing
- Use TYPING SVG URL above as a clickable image linking to blog_url or GitHub profile
- Wrap in <div align=\"center\">
- Generate 3 lines from the bio data above:
  Profile: Line1=primary role, Line2=strongest identity, Line3=fun fact or CTA
  Project: Line1=repo description, Line2=install command, Line3=\"⭐ Star this repo\"""",
    "badges_profile": """### badges (profile mode)
- Use PROFILE BADGES + SOCIAL BADGES listed above
- Wrap all in one <div align=\"center\">
- Show: portfolio, location, open-to-collaborate, pypi (if detected), npm (if detected)""",
    "badges_project": """### badges (project mode)
- Use PROJECT BADGES listed above
- Show: version, license, build (if CI detected), language version, last-commit, stars""",
    "snake": """### snake
- Use SNAKE URL as a Markdown image inside <div align=\"center\">
- After the image, add this HTML comment block:
  <!-- 
    SNAKE SETUP — Add this GitHub Action to your profile repo:
    File: .github/workflows/snake.yml
    
    name: Generate Snake Animation
    on:
      schedule: [{cron: \"0 0 * * *\"}]
      workflow_dispatch:
    permissions:
      contents: write
    jobs:
      generate:
        runs-on: ubuntu-latest
        steps:
          - uses: Platane/snk@v3
            with:
              github_user_name: ${{ github.repository_owner }}
              outputs: |
                dist/github-snake-dark.svg?palette=github-dark
    Then commit changes to the output branch.
  -->""",
    "about_profile": """### about (profile mode)
- Render a two-column HTML table, no borders
- Left cell: a JavaScript const object using bio_parsed data
  const {username_sanitized} = {
    pronouns: \"{inferred or omit field entirely}\",
    location: \"{location}\",
    education: {parsed from bio or omit},
    roles: [{roles array}],
    currentlyLearning: [{infer from recent repo topics}],
    askMeAbout: [{top languages + tools from bio}],
    funFact: \"{fun_fact}\",
    yearsOnGitHub: {years_on_github},
  };
  Wrap in a fenced js code block.
- Right cell: STATS CARD URL as a Markdown image""",
    "about_project": """### about (project mode)
- Same two-column table
- Left cell: const project = { name, type, stack, install, license, author }
- Right cell: STATS CARD URL""",
    "ventures": """### ventures (profile mode only)
- Render a 2x2 HTML table, dark surface cells (#161b22 background)
- Detect ventures from: orgs, bio @mentions, co-founder patterns in bio
- Each cell: bold name in accent color + one-line description
- If fewer than 4 found: add remaining as \"🚀 Something coming soon...\"
- Cell style: background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px""",
    "opensource": """### opensource (profile mode only)
- Render a 2x2 HTML grid using a table
- Source: pinned_repos where user is contributor (not owner) first,
  then top starred repos
- Each cell: repo name (bold), one-line description, language, ⭐stars, 🍴forks
- Mark each as \"Owner\" or \"Contributor\"
- Sort: highest-starred first. Show max 4 entries.""",
    "tech": """### tech
- Languages row: use LANGUAGE BADGES above in order
  Below each badge, no extra text needed
- Tools row: use SKILL ICONS URL above as one image
- If bio/repos suggest cybersecurity tools (kali, burpsuite, nmap, metasploit, wireshark):
  Add a \"Security Tools\" row with individual chip-style badges""",
    "stats": """### stats
- Render STATS CARD, TOP LANGUAGES CARD, STREAK CARD
- Place in a single-row HTML table, three columns, no borders
- Each wrapped in <td align=\"center\">""",
    "contrib_graph": """### contrib_graph
- Render ACTIVITY GRAPH as a full-width image
- Below it, render the three SUMMARY CARDS in a single-row table""",
    "trophies": """### trophies
- Render TROPHIES URL as a full-width image inside <div align=\"center\">""",
    "quote": """### quote
- Render DEV QUOTE URL inside <div align=\"center\">""",
    "social": """### social
- Render all SOCIAL BADGES that were detected
- Each badge is a clickable image linking to the actual profile URL
- Arrange horizontally inside <div align=\"center\">""",
    "footer": """### footer
- Render CAPSULE FOOTER URL as a Markdown image
- Below it (inside <div align=\"center\">): PROFILE VIEWS badge""",
    "features": """### features (project mode only)
- Render an HTML table with 3 columns: emoji | Feature Name | Description
- Detect features from: repo description, topics, package.json description
- Generate 4-6 features. If cannot detect, infer from project type.""",
    "install": """### install (project mode only)
- Always include: git clone, cd, install command, env setup (if .env.example found), run command
- Use detected package manager. Exact commands only.
- Wrap each block in a fenced bash code block.""",
    "usage": """### usage (project mode only)
- CLI tool: show 3-5 command examples with different flags
- Library: show import + 2 real usage code blocks
- Web App: show start command + list of key routes
- API: show 2-3 curl examples for main endpoints
- Use correct language identifier on each fenced code block""",
    "tree": """### tree (project mode only)
- Build from repo contents fetched above
- Max depth 3. Use ├── └── │ characters.
- Skip: node_modules, .git, __pycache__, dist, .next, .cache, venv
- Add # inline comments on: entry points, config files, test dirs""",
    "contribute": """### contribute (project mode only)
- Short numbered list: Fork → Clone → Branch → Commit → PR
- Add \"All contributions are welcome!\"
- Link to CODE_OF_CONDUCT.md if it exists""",
}


class ReadmeGenerator:
    """Construct prompts and call the configured LLM provider."""

    def __init__(self, gemini_api_key: str | None = None, openai_api_key: str | None = None):
        """Store provider credentials for later use."""
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    def build_system_prompt(self, output_length: str, tone: str) -> str:
        """Render the system prompt with runtime formatting values."""
        return SYSTEM_PROMPT_TEMPLATE.format(output_length=output_length, tone=tone)

    async def generate(
        self,
        context: dict[str, Any],
        config: dict[str, Any],
        built_urls: dict[str, Any],
        provider: str,
    ) -> str:
        """Generate a README using Gemini or OpenAI."""
        system_prompt = self.build_system_prompt(config["output_length"], config["tone"])
        user_prompt = build_user_prompt(context, config, built_urls)
        provider_name = provider.lower()
        if provider_name == "gemini" and not self.gemini_api_key and config.get("allow_fallback"):
            markdown = render_fallback_readme(context, config, built_urls)
        elif provider_name == "openai" and not self.openai_api_key and config.get("allow_fallback"):
            markdown = render_fallback_readme(context, config, built_urls)
        elif provider_name == "gemini":
            markdown = await self._generate_with_gemini(system_prompt, user_prompt, config)
        elif provider_name == "openai":
            markdown = await self._generate_with_openai(system_prompt, user_prompt, config)
        else:
            raise LLMError(f"Unsupported LLM provider: {provider}")
        cleaned = strip_markdown_fences(markdown)
        if not cleaned.strip():
            raise LLMError("LLM returned empty response. Try again.")
        return cleaned

    async def _generate_with_gemini(self, system_prompt: str, user_prompt: str, config: dict[str, Any]) -> str:
        """Call the Gemini API using the configured model."""
        if not self.gemini_api_key:
            raise LLMError("No API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in .env")
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise DependencyError("google-generativeai is not installed.") from exc

        def run() -> str:
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(config.get("gemini_model") or DEFAULT_GEMINI_MODEL)
            response = model.generate_content([system_prompt, user_prompt])
            return getattr(response, "text", "") or ""

        try:
            return await asyncio.to_thread(run)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini API error: {exc}\nTry --llm openai as fallback") from exc

    async def _generate_with_openai(self, system_prompt: str, user_prompt: str, config: dict[str, Any]) -> str:
        """Call the OpenAI API using the configured model."""
        if not self.openai_api_key:
            raise LLMError("No API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in .env")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise DependencyError("openai is not installed.") from exc

        def run() -> str:
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model=config.get("openai_model") or DEFAULT_OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        try:
            return await asyncio.to_thread(run)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI API error: {exc}\nTry --llm gemini as fallback") from exc


def build_user_prompt(context: dict[str, Any], config: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Construct the full user prompt passed to the LLM."""
    languages_block = _format_languages(context)
    pinned_block = _format_pinned_repos(context)
    orgs_block = _format_organizations(context)
    socials_block = _format_socials(context)
    section_block = _build_section_instruction_block(context, config)
    project_block = _format_project_block(context)
    existing_readme = safe_excerpt(context.get("existing_readme"), limit=1800) or "None"

    return f"""
## GITHUB DATA (fetched and structured)

USERNAME: {context['username']}
DISPLAY NAME: {context['display_name']}
LOCATION: {context.get('location') or 'Unknown'}
BIO (raw): {context.get('bio') or 'None'}
BIO PARSED:
  Roles: {context['bio_parsed'].get('roles') or []}
  Stack keywords: {context['bio_parsed'].get('stack_keywords') or []}
  Education: {context['bio_parsed'].get('education')}
  Ventures: {context['bio_parsed'].get('ventures') or []}
  Fun fact: {context['bio_parsed'].get('fun_fact')}
  Ask me about: {context['bio_parsed'].get('ask_me_about') or []}
YEARS ON GITHUB: {context['years_on_github']}
PUBLIC REPOS: {context['public_repos']}
FOLLOWERS: {context['followers']}
TOTAL STARS: {context['total_stars']}
TOTAL COMMITS: {context['total_commits']}
TOTAL PRs: {context['total_prs']}

LANGUAGES:
{languages_block}

PINNED REPOS:
{pinned_block}

ORGANIZATIONS:
{orgs_block}

SOCIAL LINKS DETECTED:
{socials_block}

EXISTING README EXCERPT:
{existing_readme}

{project_block}
---

## CONFIG

MODE: {context['mode']}
COLOR: #{config['color']}
GRADIENT: {config['gradient']}
HEADER TYPE: {config['header_type']}
ANIMATION: {config['animation']}
FONT: {config['font']}
STATS THEME: {config['stats_theme']}
BADGE STYLE: {config['badge_style']}
CAPSULE HEIGHT: {config['height']}
SELECTED ICONS: {config['icons']}
SECTIONS TO RENDER (in order): {config['sections']}
OUTPUT LENGTH: {config['output_length']} lines

---

## PRE-BUILT URLS (use these exactly, do not modify)

CAPSULE HEADER:
{built_urls['capsule_header_url']}

CAPSULE FOOTER:
{built_urls['capsule_footer_url']}

TYPING SVG:
{built_urls['typing_svg_url']}

SNAKE ANIMATION:
{built_urls['snake_url']}

STATS CARD:
{built_urls['stats_card_url']}

TOP LANGUAGES CARD:
{built_urls['top_langs_url']}

STREAK CARD:
{built_urls['streak_url']}

ACTIVITY GRAPH:
{built_urls['activity_graph_url']}

SUMMARY CARDS:
{built_urls['summary_cards_urls'][0]}
{built_urls['summary_cards_urls'][1]}
{built_urls['summary_cards_urls'][2]}

TROPHIES:
{built_urls['trophies_url']}

DEV QUOTE:
{built_urls['quote_url']}

PROFILE VIEWS:
{built_urls['views_counter_url']}

LANGUAGE BADGES (in order of prevalence):
{_format_markdown_lines(built_urls['language_badges'])}

SKILL ICONS (user selected + auto-detected):
{built_urls['skillicons_url']}

SOCIAL BADGES (only detected platforms):
{_format_markdown_lines(built_urls['social_badges'])}

PROFILE BADGES:
{_format_markdown_lines(built_urls['profile_badges'])}

PROJECT BADGES:
{_format_markdown_lines(built_urls['project_badges'])}

---

## SECTION INSTRUCTIONS

{section_block}

---

## SELF-REVIEW CHECKLIST
Before outputting, verify:
□ No placeholder text remains ({{USERNAME}}, etc.)
□ All URLs are on single lines, not wrapped
□ Section order matches SECTIONS list exactly
□ HTML tables have no visible borders
□ Snake comment block is present if snake section is active
□ Capsule header and footer URLs are complete
□ Typing SVG lines are properly encoded
□ No AI/tool mentions anywhere in output
□ Output starts directly with the README content
""".strip()


def _format_languages(context: dict[str, Any]) -> str:
    """Format language lines for the prompt."""
    lines = [
        f"  {language}: {data['percent']}% — {data['proficiency']} — hex #{data['hex']}"
        for language, data in context.get("languages", {}).items()
    ]
    return "\n".join(lines) or "  None"


def _format_pinned_repos(context: dict[str, Any]) -> str:
    """Format pinned repository lines for the prompt."""
    lines = [
        f"  - {repo['name']}: {repo.get('description') or 'No description'} | ⭐{repo.get('stars', 0)} | 🍴{repo.get('forks', 0)} | {repo.get('language') or 'Unknown'}"
        for repo in context.get("pinned_repos", [])
    ]
    return "\n".join(lines) or "  None"


def _format_organizations(context: dict[str, Any]) -> str:
    """Format organization lines for the prompt."""
    lines = [
        f"  - {org['login']}: {org.get('description') or 'No description'}"
        for org in context.get("orgs", [])
    ]
    return "\n".join(lines) or "  None"


def _format_socials(context: dict[str, Any]) -> str:
    """Format social link lines for the prompt."""
    lines = [f"  {platform}: {url}" for platform, url in context.get("social_links", {}).items()]
    return "\n".join(lines) or "  None"


def _format_project_block(context: dict[str, Any]) -> str:
    """Format project-specific context for project mode."""
    project = context.get("project")
    if not project:
        return ""
    return f"""
PROJECT MODE DATA:
PROJECT NAME: {project['name']}
PROJECT DESCRIPTION: {project.get('description') or 'None'}
PROJECT TYPE: {project.get('type')}
PROJECT STACK: {project.get('stack')}
PROJECT LICENSE: {project.get('license')}
PROJECT VERSION: {project.get('version')}
INSTALL COMMAND: {project.get('install_command')}
RUN COMMAND: {project.get('run_command')}
ENV VARS: {project.get('env_vars')}
HAS DOCKER: {project.get('has_docker')}
HAS CI: {project.get('has_ci')}
LAST COMMIT DATE: {project.get('last_commit_date')}
PROJECT TREE:
{project.get('tree') or 'None'}
""".strip()


def _format_markdown_lines(items: list[str]) -> str:
    """Format a list of Markdown lines for prompt inclusion."""
    return "\n".join(f"  {item}" for item in items) or "  None"


def _build_section_instruction_block(context: dict[str, Any], config: dict[str, Any]) -> str:
    """Build section-specific instructions in configured order."""
    blocks: list[str] = []
    for section in config["sections"]:
        key = section
        if section == "badges":
            key = "badges_profile" if context["mode"] == "profile" else "badges_project"
        elif section == "about":
            key = "about_profile" if context["mode"] == "profile" else "about_project"
        instruction = SECTION_INSTRUCTIONS.get(key)
        if instruction:
            blocks.append(instruction)
    return "\n\n".join(blocks)



