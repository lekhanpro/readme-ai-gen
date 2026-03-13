"""Orchestration layer for preparing and generating README output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .builder import ReadmeBuilder
from .fetcher import GitHubFetcher
from .generator import ReadmeGenerator
from .utils import detect_icons_from_context


@dataclass
class PreparedReadme:
    """Container for fetched context, normalized config, and built URLs."""

    context: dict[str, Any]
    config: dict[str, Any]
    built_urls: dict[str, Any]


class ReadmeRenderer:
    """Prepare context and invoke the configured generator."""

    def __init__(self, generator: ReadmeGenerator | None = None):
        """Store a reusable generator instance."""
        self.generator = generator or ReadmeGenerator()

    async def prepare(
        self,
        url: str,
        config: dict[str, Any],
        github_token: str | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> PreparedReadme:
        """Fetch GitHub data and pre-build all third-party asset URLs."""
        fetcher = GitHubFetcher(url, token=github_token)
        fetcher.status_callback = status_callback
        context = await fetcher.fetch_all()

        normalized_config = dict(config)
        if not normalized_config.get("icons"):
            normalized_config["icons"] = detect_icons_from_context(context)

        builder = ReadmeBuilder(context, normalized_config)
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
            "skillicons_url": builder.build_skillicons_url(normalized_config["icons"]),
            "views_counter_url": builder.build_views_counter_url(),
            "language_badges": builder.build_language_badges(),
            "social_badges": builder.build_social_badges(),
            "profile_badges": builder.build_profile_badges(),
            "project_badges": builder.build_project_badges() if context["mode"] == "project" else [],
        }
        return PreparedReadme(context=context, config=normalized_config, built_urls=built_urls)

    async def generate(
        self,
        prepared: PreparedReadme,
        provider: str,
        status_callback: Callable[[str], None] | None = None,
    ) -> str:
        """Generate Markdown from a prepared context and built URLs."""
        if status_callback:
            status_callback(f"Calling {provider.title()} API...")
        return await self.generator.generate(prepared.context, prepared.config, prepared.built_urls, provider)

    async def render(
        self,
        url: str,
        config: dict[str, Any],
        provider: str,
        github_token: str | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> tuple[PreparedReadme, str]:
        """Prepare context and generate the final README in one call."""
        prepared = await self.prepare(url, config, github_token=github_token, status_callback=status_callback)
        markdown = await self.generate(prepared, provider, status_callback=status_callback)
        return prepared, markdown
