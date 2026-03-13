"""Deterministic README rendering used when no LLM provider is configured."""

from __future__ import annotations

from typing import Any

from .utils import ensure_url_scheme, safe_excerpt, slugify_identifier


SECTION_HEADINGS = {
    "about": "# About",
    "ventures": "# Ventures",
    "opensource": "# Open Source",
    "tech": "# Tech Arsenal",
    "stats": "# Stats",
    "contrib_graph": "# Contribution Graph",
    "trophies": "# Trophies",
    "quote": "# Quote",
    "social": "# Socials",
    "features": "# Features",
    "install": "# Installation",
    "usage": "# Usage",
    "tree": "# Project Structure",
    "contribute": "# Contributing",
    "snake": "# Snake",
}


def render_fallback_readme(context: dict[str, Any], config: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render a complete README without calling an LLM."""
    sections = config["sections"]
    output: list[str] = []

    hero = _render_hero(context, config, built_urls)
    if hero:
        output.append(hero)

    for section in sections:
        if section in {"header", "typing", "badges", "footer"}:
            continue
        rendered = _render_section(section, context, config, built_urls)
        if not rendered:
            continue
        output.append("---")
        output.append(rendered)

    footer = _render_footer(context, built_urls)
    if footer:
        output.append("---")
        output.append(footer)

    return "\n\n".join(part.strip() for part in output if part).strip() + "\n"


def _render_hero(context: dict[str, Any], config: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the centered header, typing banner, and badges cluster."""
    parts = ["<div align=\"center\">"]
    if "header" in config["sections"]:
        parts.append(f"![Header]({built_urls['capsule_header_url']})")
    if "typing" in config["sections"]:
        target = ensure_url_scheme(context.get("blog_url") or f"github.com/{context['username']}")
        parts.append(f"[![Typing SVG]({built_urls['typing_svg_url']})]({target})")
    if "badges" in config["sections"]:
        badges = built_urls["project_badges"] if context["mode"] == "project" else built_urls["profile_badges"] + built_urls["social_badges"]
        parts.extend(badges)
    parts.append("</div>")
    return "\n\n".join(parts)


def _render_section(section: str, context: dict[str, Any], config: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Dispatch a single section render."""
    handlers = {
        "snake": _render_snake,
        "about": _render_about,
        "ventures": _render_ventures,
        "opensource": _render_opensource,
        "tech": _render_tech,
        "stats": _render_stats,
        "contrib_graph": _render_contrib_graph,
        "trophies": _render_trophies,
        "quote": _render_quote,
        "social": _render_social,
        "features": _render_features,
        "install": _render_install,
        "usage": _render_usage,
        "tree": _render_tree,
        "contribute": _render_contribute,
    }
    handler = handlers.get(section)
    if not handler:
        return ""
    return handler(context, config, built_urls)


def _render_snake(_: dict[str, Any], __: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the snake section."""
    return "\n".join(
        [
            SECTION_HEADINGS["snake"],
            "<div align=\"center\">",
            f"![snake]({built_urls['snake_url']})",
            "</div>",
            "<!--",
            "SNAKE SETUP — Add this GitHub Action to your profile repo:",
            "File: .github/workflows/snake.yml",
            "name: Generate Snake Animation",
            "on:",
            "  schedule: [{cron: \"0 0 * * *\"}]",
            "  workflow_dispatch:",
            "permissions:",
            "  contents: write",
            "jobs:",
            "  generate:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - uses: Platane/snk@v3",
            "        with:",
            "          github_user_name: ${{ github.repository_owner }}",
            "          outputs: |",
            "            dist/github-snake-dark.svg?palette=github-dark",
            "Then commit changes to the output branch.",
            "-->",
        ]
    )


def _render_about(context: dict[str, Any], _: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the about table for profile or project mode."""
    if context["mode"] == "project":
        project = context["project"]
        code = "\n".join(
            [
                "```js",
                "const project = {",
                f"  name: \"{project['name']}\",",
                f"  type: \"{project['type']}\",",
                f"  stack: {project.get('stack') or []},",
                f"  install: \"{project.get('install_command')}\",",
                f"  license: \"{project.get('license')}\",",
                f"  author: \"{context['username']}\"",
                "};",
                "```",
            ]
        )
    else:
        bio = context.get("bio_parsed", {})
        identifier = slugify_identifier(context["username"])
        code = "\n".join(
            [
                "```js",
                f"const {identifier} = {{",
                f"  location: \"{context.get('location') or 'Unknown'}\",",
                f"  education: {bio.get('education')},",
                f"  roles: {bio.get('roles') or []},",
                f"  currentlyLearning: {(context.get('all_topics') or [])[:4]},",
                f"  askMeAbout: {bio.get('ask_me_about') or []},",
                f"  funFact: \"{bio.get('fun_fact') or 'Building in public.'}\",",
                f"  yearsOnGitHub: {context.get('years_on_github', 0)}",
                "};",
                "```",
            ]
        )
    return "\n".join(
        [
            SECTION_HEADINGS["about"],
            "<table>",
            "  <tr>",
            "    <td style=\"border:none\" valign=\"top\" width=\"58%\">",
            code,
            "    </td>",
            "    <td style=\"border:none\" valign=\"top\" width=\"42%\">",
            f"      <img src=\"{built_urls['stats_card_url']}\" alt=\"Stats card\" />",
            "    </td>",
            "  </tr>",
            "</table>",
        ]
    )


def _render_ventures(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render ventures cards for profile mode."""
    ventures = [*context.get("bio_parsed", {}).get("ventures", []), *[org["login"] for org in context.get("orgs", [])]]
    ventures = ventures[:4]
    while len(ventures) < 4:
        ventures.append("Something coming soon")
    cells = []
    for venture in ventures[:4]:
        cells.append(
            f"<td style=\"border:none;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px;\"><strong>{venture}</strong><br/>Focused builder lane or open-source initiative.</td>"
        )
    return "\n".join(
        [
            SECTION_HEADINGS["ventures"],
            "<table>",
            f"  <tr>{cells[0]}{cells[1]}</tr>",
            f"  <tr>{cells[2]}{cells[3]}</tr>",
            "</table>",
        ]
    )


def _render_opensource(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render pinned and top repositories for profile mode."""
    repos = (context.get("pinned_repos") or []) + (context.get("top_repos") or [])
    seen: set[str] = set()
    selected = []
    for repo in repos:
        name = repo.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        selected.append(repo)
        if len(selected) == 4:
            break
    if not selected:
        return ""
    rows = []
    for repo in selected:
        owner_label = "Owner" if repo.get("owner", context["username"]) == context["username"] else "Contributor"
        rows.append(
            f"<td style=\"border:none;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px;\"><strong>{repo.get('name')}</strong><br/>{repo.get('description') or 'No description yet.'}<br/>{repo.get('language') or 'Unknown'} · ⭐{repo.get('stars', 0)} · 🍴{repo.get('forks', 0)} · {owner_label}</td>"
        )
    while len(rows) < 4:
        rows.append("<td style=\"border:none;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px;\"><strong>More contributions</strong><br/>Additional open-source work lands here.</td>")
    return "\n".join(
        [
            SECTION_HEADINGS["opensource"],
            "<table>",
            f"  <tr>{rows[0]}{rows[1]}</tr>",
            f"  <tr>{rows[2]}{rows[3]}</tr>",
            "</table>",
        ]
    )


def _render_tech(context: dict[str, Any], _: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render languages and tools rows."""
    language_badges = built_urls.get("language_badges") or ["No language data detected."]
    lines = [SECTION_HEADINGS["tech"], "**Languages**", "<div align=\"center\">", *language_badges, "</div>"]
    lines.extend(["", "**Tools**", "<div align=\"center\">", f"![Skill Icons]({built_urls['skillicons_url']})", "</div>"])
    return "\n".join(lines)


def _render_stats(_: dict[str, Any], __: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the three-card stats table."""
    return "\n".join(
        [
            SECTION_HEADINGS["stats"],
            "<table>",
            "  <tr>",
            f"    <td style=\"border:none\" align=\"center\"><img src=\"{built_urls['stats_card_url']}\" alt=\"Stats\" /></td>",
            f"    <td style=\"border:none\" align=\"center\"><img src=\"{built_urls['top_langs_url']}\" alt=\"Top languages\" /></td>",
            f"    <td style=\"border:none\" align=\"center\"><img src=\"{built_urls['streak_url']}\" alt=\"Streak\" /></td>",
            "  </tr>",
            "</table>",
        ]
    )


def _render_contrib_graph(_: dict[str, Any], __: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the contribution graph and summary cards."""
    cards = built_urls["summary_cards_urls"]
    return "\n".join(
        [
            SECTION_HEADINGS["contrib_graph"],
            f"![Contribution Graph]({built_urls['activity_graph_url']})",
            "<table>",
            "  <tr>",
            f"    <td style=\"border:none\"><img src=\"{cards[0]}\" alt=\"Profile details\" /></td>",
            f"    <td style=\"border:none\"><img src=\"{cards[1]}\" alt=\"Repos per language\" /></td>",
            f"    <td style=\"border:none\"><img src=\"{cards[2]}\" alt=\"Most commit language\" /></td>",
            "  </tr>",
            "</table>",
        ]
    )


def _render_trophies(_: dict[str, Any], __: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the trophy section."""
    return "\n".join([SECTION_HEADINGS["trophies"], "<div align=\"center\">", f"![Trophies]({built_urls['trophies_url']})", "</div>"])


def _render_quote(_: dict[str, Any], __: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the quote section."""
    return "\n".join([SECTION_HEADINGS["quote"], "<div align=\"center\">", f"![Quote]({built_urls['quote_url']})", "</div>"])


def _render_social(context: dict[str, Any], _: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render clickable social badges."""
    badges = built_urls.get("social_badges")
    if not badges:
        return ""
    return "\n".join([SECTION_HEADINGS["social"], "<div align=\"center\">", *badges, "</div>"])


def _render_features(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render deterministic project feature rows."""
    project = context["project"]
    features = [
        ("⚡", project["type"], project.get("description") or "Structured output generation from repository metadata."),
        ("🧠", "Context-first generation", "Fetches GitHub data before building README content."),
        ("🎛️", "Configurable visuals", "Controls theme, header style, sections, icons, and badge styling."),
        ("🌐", "Web + CLI surface", "Works as a terminal tool and as a Vercel-friendly website."),
    ]
    rows = [f"  <tr><td>{emoji}</td><td><strong>{name}</strong></td><td>{desc}</td></tr>" for emoji, name, desc in features]
    return "\n".join([SECTION_HEADINGS["features"], "<table>", *rows, "</table>"])


def _render_install(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render installation steps for project mode."""
    project = context["project"]
    clone_url = f"https://github.com/{context['username']}/{context['repo']}"
    blocks = [
        "```bash",
        f"git clone {clone_url}",
        f"cd {context['repo']}",
        project.get("install_command") or "# Add install command",
        "```",
    ]
    if project.get("env_vars"):
        blocks.extend(["", "```bash", "cp .env.example .env", "```"])
    blocks.extend(["", "```bash", project.get("run_command") or "# Add run command", "```"])
    return "\n".join([SECTION_HEADINGS["install"], *blocks])


def _render_usage(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render mode-specific usage examples for project mode."""
    project = context["project"]
    repo_url = f"https://github.com/{context['username']}/{context['repo']}"
    if project.get("type") == "CLI Tool":
        snippet = [
            "```bash",
            f"readme-gen {repo_url}",
            f"readme-gen {repo_url} --mode project --color 06B6D4",
            f"readme-gen https://github.com/{context['username']} --mode profile --dry-run",
            "```",
        ]
    else:
        snippet = ["```bash", project.get("run_command") or "# Add usage example", "```"]
    return "\n".join([SECTION_HEADINGS["usage"], *snippet])


def _render_tree(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render the repository tree."""
    tree = context["project"].get("tree")
    if not tree:
        return ""
    return "\n".join([SECTION_HEADINGS["tree"], "```text", tree, "```"])


def _render_contribute(context: dict[str, Any], _: dict[str, Any], __: dict[str, Any]) -> str:
    """Render contribution steps."""
    repo_url = f"https://github.com/{context['username']}/{context['repo']}"
    return "\n".join(
        [
            SECTION_HEADINGS["contribute"],
            "1. Fork the repository.",
            f"2. Clone your fork of `{repo_url}`.",
            "3. Create a feature branch.",
            "4. Commit your changes with clear messages.",
            "5. Open a pull request.",
            "",
            "All contributions are welcome!",
        ]
    )


def _render_footer(context: dict[str, Any], built_urls: dict[str, Any]) -> str:
    """Render the closing footer block."""
    if "footer" not in built_urls.get("capsule_footer_url", "") and not built_urls.get("capsule_footer_url"):
        return ""
    lines = ["<div align=\"center\">", f"![Footer]({built_urls['capsule_footer_url']})", f"![Views]({built_urls['views_counter_url']})", "</div>"]
    if context.get("mode") == "project":
        lines.append(f"<p align=\"center\">Generated for `{context['username']}/{context['repo']}`.</p>")
    return "\n".join(lines)
