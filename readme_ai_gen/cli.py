"""Click CLI entry point for readme-ai-gen."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import click
from click.core import ParameterSource
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .builder import ReadmeBuilder
from .config import (
    ALL_ICONS,
    DEFAULT_ANIMATION,
    DEFAULT_BADGE_STYLE,
    DEFAULT_FONT,
    DEFAULT_HEADER,
    DEFAULT_HEIGHT,
    DEFAULT_LLM,
    DEFAULT_OUTPUT,
    DEFAULT_OUTPUT_LENGTH,
    DEFAULT_STATS_THEME,
    DEFAULT_TONE,
    FONTS,
    HEADER_TYPES,
    PROFILE_SECTIONS_DEFAULT,
    PROJECT_SECTIONS_DEFAULT,
    THEMES,
)
from .generator import ReadmeGenerator
from .renderer import PreparedReadme, ReadmeRenderer
from .utils import (
    DependencyError,
    GitHubAPIError,
    LLMError,
    URLParseError,
    count_lines,
    detect_icons_from_context,
    get_default_sections,
    order_sections,
    parse_csv_list,
    parse_github_url,
    resolve_theme,
)

console = Console()


@click.command()
@click.argument("url")
@click.option("--mode", type=click.Choice(["auto", "profile", "project"]), default="auto")
@click.option("--color", default=None)
@click.option("--header", "header_type", type=click.Choice(HEADER_TYPES), default=None)
@click.option("--animation", default=None)
@click.option("--font", default=None)
@click.option("--stats-theme", default=None)
@click.option("--badge-style", default=None)
@click.option("--height", type=int, default=None)
@click.option("--sections", default=None)
@click.option("--icons", default=None)
@click.option("--llm", type=click.Choice(["nvidia", "groq", "gemini", "openai"]), default=None)
@click.option("--output", default=None)
@click.option("--copy", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def main(
    ctx: click.Context,
    url: str,
    mode: str,
    color: str | None,
    header_type: str | None,
    animation: str | None,
    font: str | None,
    stats_theme: str | None,
    badge_style: str | None,
    height: int | None,
    sections: str | None,
    icons: str | None,
    llm: str | None,
    output: str | None,
    copy: bool,
    dry_run: bool,
) -> None:
    """Generate a premium README from a GitHub profile or repository URL."""
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    default_llm = os.getenv("DEFAULT_LLM", DEFAULT_LLM)
    default_output = os.getenv("DEFAULT_OUTPUT", DEFAULT_OUTPUT)

    try:
        _, repo, detected_mode = parse_github_url(url)
        resolved_mode = _resolve_mode(mode, detected_mode, repo)
        renderer = ReadmeRenderer(generator=ReadmeGenerator())

        if _should_launch_wizard(ctx):
            prepared, provider, final_output, copy_flag, dry_run_flag = _run_wizard(
                renderer=renderer,
                url=url,
                mode=resolved_mode,
                github_token=github_token,
                default_llm=default_llm,
                default_output=default_output,
            )
            copy = copy_flag
            dry_run = dry_run_flag
            output = final_output
        else:
            config = _build_config(
                mode=resolved_mode,
                color=color,
                header_type=header_type,
                animation=animation,
                font=font,
                stats_theme=stats_theme,
                badge_style=badge_style,
                height=height,
                sections=sections,
                icons=icons,
                llm=llm or default_llm,
                output=output or default_output,
            )
            prepared = asyncio.run(
                _prepare_with_progress(renderer, url, config, github_token=github_token)
            )
            _print_summary_panel(prepared)
            provider = config["llm"]
            output = config["output"]

        markdown = asyncio.run(_generate_with_progress(renderer, prepared, provider))
        line_count = count_lines(markdown)

        if dry_run:
            console.print(Panel(markdown, title="README Preview", border_style="cyan"))
            console.print(f"[green]✓[/green] README generated ({line_count} lines)")
            if copy:
                console.print("[yellow]![/yellow] --dry-run prevents clipboard writes; skipping copy.")
            return

        output_path = Path(output or default_output)
        output_path.write_text(markdown, encoding="utf-8")
        console.print(f"[green]✓[/green] README generated ({line_count} lines)")
        console.print(f"[green]✓[/green] Written to {output_path}")

        if copy:
            _copy_to_clipboard(markdown)
            console.print("[green]✓[/green] Copied to clipboard")

        console.print(
            Panel(
                f"[green]✓[/green] README.md written ({line_count} lines)\n[dim]Path: {output_path}[/dim]",
                title="Done",
                border_style="green",
            )
        )
    except (URLParseError, GitHubAPIError, LLMError, DependencyError, ValueError) as exc:
        _print_error_panel(exc)
        raise SystemExit(1) from exc


async def _prepare_with_progress(
    renderer: ReadmeRenderer,
    url: str,
    config: dict[str, Any],
    *,
    github_token: str | None,
) -> PreparedReadme:
    """Prepare README context while streaming progress updates."""
    with Progress(SpinnerColumn(), TextColumn("[purple]{task.description}"), console=console) as progress:
        task = progress.add_task("Fetching GitHub profile...", total=None)

        def update(message: str) -> None:
            progress.update(task, description=message)

        prepared = await renderer.prepare(
            url,
            config,
            github_token=github_token,
            status_callback=update,
        )
    return prepared


async def _generate_with_progress(
    renderer: ReadmeRenderer,
    prepared: PreparedReadme,
    provider: str,
) -> str:
    """Generate README Markdown while streaming progress updates."""
    with Progress(SpinnerColumn(), TextColumn("[purple]{task.description}"), console=console) as progress:
        task = progress.add_task(f"Calling {provider.title()} API...", total=None)

        def update(message: str) -> None:
            progress.update(task, description=message)

        markdown = await renderer.generate(prepared, provider, status_callback=update)
    return markdown


def _build_config(
    *,
    mode: str,
    color: str | None,
    header_type: str | None,
    animation: str | None,
    font: str | None,
    stats_theme: str | None,
    badge_style: str | None,
    height: int | None,
    sections: str | None,
    icons: str | None,
    llm: str,
    output: str,
) -> dict[str, Any]:
    """Normalize CLI and wizard inputs into one config dictionary."""
    theme = resolve_theme(color)
    selected_sections = parse_csv_list(sections) or get_default_sections(mode)
    ordered_sections = order_sections({"header", *selected_sections, "footer"})
    return {
        "mode": mode,
        "theme": theme["name"],
        "color": theme["hex"],
        "gradient": theme["gradient"],
        "header_type": header_type or DEFAULT_HEADER,
        "animation": animation or DEFAULT_ANIMATION,
        "font": (font or DEFAULT_FONT).replace("+", " "),
        "stats_theme": stats_theme or DEFAULT_STATS_THEME,
        "badge_style": badge_style or DEFAULT_BADGE_STYLE,
        "height": height or DEFAULT_HEIGHT,
        "sections": ordered_sections,
        "icons": parse_csv_list(icons),
        "llm": llm,
        "gemini_model": os.getenv("GEMINI_MODEL") or None,
        "openai_model": os.getenv("OPENAI_MODEL") or None,
        "groq_model": os.getenv("GROQ_MODEL") or None,
        "nvidia_model": os.getenv("NVIDIA_MODEL") or None,
        "output": output,
        "output_length": DEFAULT_OUTPUT_LENGTH,
        "tone": DEFAULT_TONE,
    }


def _resolve_mode(mode: str, detected_mode: str, repo: str | None) -> str:
    """Resolve explicit or automatic mode selection against the URL shape."""
    if mode == "auto":
        return detected_mode
    if mode == "project" and not repo:
        raise URLParseError("For project mode, use: https://github.com/username/repo-name")
    if mode == "profile" and repo:
        raise URLParseError("Could not parse GitHub URL. Expected: https://github.com/username")
    return mode


def _should_launch_wizard(ctx: click.Context) -> bool:
    """Return True when the command was invoked with only the URL argument."""
    option_names = [
        "mode",
        "color",
        "header_type",
        "animation",
        "font",
        "stats_theme",
        "badge_style",
        "height",
        "sections",
        "icons",
        "llm",
        "output",
        "copy",
        "dry_run",
    ]
    return all(ctx.get_parameter_source(name) == ParameterSource.DEFAULT for name in option_names)


def _run_wizard(
    *,
    renderer: ReadmeRenderer,
    url: str,
    mode: str,
    github_token: str | None,
    default_llm: str,
    default_output: str,
) -> tuple[PreparedReadme, str, str, bool, bool]:
    """Run the interactive configuration wizard."""
    try:
        import questionary
    except ImportError as exc:
        raise DependencyError("Interactive mode requires questionary. Install project dependencies first.") from exc

    mode_choice = questionary.select(
        "Step 1/6 — Mode",
        choices=[
            questionary.Choice("Auto-detect from URL", value=mode),
            questionary.Choice("Profile README", value="profile"),
            questionary.Choice("Project README", value="project"),
        ],
        default=mode,
    ).ask()
    resolved_mode = _resolve_mode(mode_choice or mode, mode, parse_github_url(url)[1])

    color_map = {
        "Purple  (#A855F7)": "purple",
        "Cyan    (#06B6D4)": "cyan",
        "Green   (#22C55E)": "green",
        "Orange  (#F97316)": "orange",
        "Pink    (#EC4899)": "pink",
        "Red     (#EF4444)": "red",
        "Gold    (#EAB308)": "gold",
        "Blue    (#3B82F6)": "blue",
        "Teal    (#14B8A6)": "teal",
        "Slate   (#94A3B8)": "slate",
        "Custom": "custom",
    }
    color_choice = questionary.select(
        "Step 2/6 — Color Theme",
        choices=list(color_map.keys()),
        default="Purple  (#A855F7)",
    ).ask()
    color_value = color_map[color_choice or "Purple  (#A855F7)"]
    if color_value == "custom":
        color_value = questionary.text("Enter a custom hex color", default="#A855F7").ask() or "#A855F7"

    header_value = questionary.select(
        "Step 3/6 — Header Style",
        choices=HEADER_TYPES,
        default=DEFAULT_HEADER,
    ).ask() or DEFAULT_HEADER

    default_sections = get_default_sections(resolved_mode)
    section_choices = PROFILE_SECTIONS_DEFAULT if resolved_mode == "profile" else PROJECT_SECTIONS_DEFAULT
    selected_sections = questionary.checkbox(
        "Step 4/6 — Sections to include",
        choices=[questionary.Choice(section, checked=section in default_sections) for section in section_choices],
    ).ask() or default_sections

    temp_config = _build_config(
        mode=resolved_mode,
        color=color_value,
        header_type=header_value,
        animation=DEFAULT_ANIMATION,
        font=DEFAULT_FONT,
        stats_theme=DEFAULT_STATS_THEME,
        badge_style=DEFAULT_BADGE_STYLE,
        height=DEFAULT_HEIGHT,
        sections=",".join(selected_sections),
        icons=None,
        llm=default_llm,
        output=default_output,
    )
    preview = asyncio.run(_prepare_with_progress(renderer, url, temp_config, github_token=github_token))

    default_icons = preview.config.get("icons") or detect_icons_from_context(preview.context)
    icon_choices = [questionary.Choice(icon, checked=icon in default_icons) for icon in ALL_ICONS]
    selected_icons = questionary.checkbox(
        "Step 5/6 — Tech Icons",
        choices=icon_choices,
    ).ask() or default_icons

    llm_choice = questionary.select(
        "Step 6/6 — LLM Provider",
        choices=[
            questionary.Choice("NVIDIA (qwen/qwen3.5-397b-a17b)", value="nvidia"),
            questionary.Choice("Groq (llama-3.3-70b-versatile)", value="groq"),
            questionary.Choice("Gemini (gemini-1.5-flash)", value="gemini"),
            questionary.Choice("OpenAI (gpt-4o-mini)", value="openai"),
        ],
        default=default_llm,
    ).ask() or default_llm

    final_config = _build_config(
        mode=resolved_mode,
        color=color_value,
        header_type=header_value,
        animation=DEFAULT_ANIMATION,
        font=DEFAULT_FONT,
        stats_theme=DEFAULT_STATS_THEME,
        badge_style=DEFAULT_BADGE_STYLE,
        height=DEFAULT_HEIGHT,
        sections=",".join(selected_sections),
        icons=",".join(selected_icons),
        llm=llm_choice,
        output=default_output,
    )
    prepared = _rebuild_prepared(preview.context, final_config)
    _print_summary_panel(prepared)

    should_generate = questionary.confirm("Generate README?", default=True).ask()
    if not should_generate:
        raise click.Abort()

    return prepared, llm_choice, final_config["output"], False, False


def _rebuild_prepared(context: dict[str, Any], config: dict[str, Any]) -> PreparedReadme:
    """Rebuild URLs locally after interactive config changes."""
    builder = ReadmeBuilder(context, config)
    built_urls = {
        "capsule_header_url": builder.build_capsule_header_url(),
        "capsule_footer_url": builder.build_footer_url(),
        "typing_svg_url": builder.build_typing_svg_url(),
        "snake_url": builder.build_snake_url(),
        "stats_card_url": builder.build_stats_card_url(),
        "top_langs_url": builder.build_top_langs_url(),
        "streak_url": builder.build_streak_url(),
        "activity_graph_url": builder.build_activity_graph_url(),
        "summary_cards_urls": builder.build_summary_cards_urls(),
        "trophies_url": builder.build_trophies_url(),
        "quote_url": builder.build_quotes_url(),
        "skillicons_url": builder.build_skillicons_url(config["icons"]),
        "views_counter_url": builder.build_views_counter_url(),
        "language_badges": builder.build_language_badges(),
        "social_badges": builder.build_social_badges(),
        "profile_badges": builder.build_profile_badges(),
        "project_badges": builder.build_project_badges() if context["mode"] == "project" else [],
    }
    return PreparedReadme(context=context, config=config, built_urls=built_urls)


def _print_summary_panel(prepared: PreparedReadme) -> None:
    """Render the fetched-data summary panel shown before generation."""
    context = prepared.context
    config = prepared.config
    top_languages = [
        f"{name} ({data['proficiency']})"
        for name, data in list(context.get("languages", {}).items())[:2]
    ]
    socials = " · ".join(context.get("social_links", {}).keys()) or "none"
    body = (
        f"📊 GitHub Data Fetched\n\n"
        f"User        {context['display_name']} (@{context['username']})\n"
        f"Location    {context.get('location') or 'Unknown'}\n"
        f"Repos       {context['public_repos']}   Stars    {context['total_stars']}   Followers  {context['followers']}\n"
        f"Languages   {' · '.join(top_languages) if top_languages else 'None detected'}\n"
        f"Pinned      {len(context.get('pinned_repos', []))} repos found\n"
        f"Socials     {socials}\n\n"
        f"Mode        {context['mode'].title()} README\n"
        f"Color       ████ #{config['color']} ({config['theme']})\n"
        f"Sections    {len(config['sections'])} active"
    )
    console.print(Panel(body, border_style="magenta"))


def _copy_to_clipboard(text: str) -> None:
    """Copy Markdown text to the system clipboard."""
    try:
        import pyperclip
    except ImportError as exc:
        raise DependencyError("Clipboard support requires pyperclip. Install project dependencies first.") from exc
    pyperclip.copy(text)


def _print_error_panel(exc: Exception) -> None:
    """Render a rich error panel."""
    console.print(Panel(str(exc), title="Error", border_style="red"))


if __name__ == "__main__":
    main()
