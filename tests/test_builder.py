"""Unit tests for URL construction helpers."""

from __future__ import annotations

import unittest

from readme_ai_gen.builder import ReadmeBuilder


PROFILE_CONTEXT = {
    "mode": "profile",
    "username": "mithun50",
    "display_name": "Mithun Gowda",
    "bio": "Python engineer building open source tools.",
    "bio_parsed": {
        "roles": ["Engineer"],
        "stack_keywords": ["Python", "Fastapi", "Docker"],
        "fun_fact": "Builds developer tooling at night.",
    },
    "location": "Karnataka, India",
    "public_repos": 89,
    "followers": 148,
    "total_stars": 528,
    "has_pypi": True,
    "has_npm": False,
    "social_links": {
        "portfolio": "mithungowda.in",
        "linkedin": "https://linkedin.com/in/mithungowdab",
    },
    "languages": {
        "Python": {"percent": 68.2, "proficiency": "Expert", "hex": "3776AB"},
        "TypeScript": {"percent": 22.1, "proficiency": "Advanced", "hex": "3178C6"},
    },
    "project": None,
}

PROJECT_CONTEXT = {
    **PROFILE_CONTEXT,
    "mode": "project",
    "project": {
        "name": "readme-ai-gen",
        "description": "Generate premium GitHub READMEs from any URL.",
        "version": "1.0.0",
        "license": "MIT License",
        "type": "CLI Tool",
        "stack": ["Python", "Click", "Rich"],
        "install_command": "pip install readme-ai-gen",
        "run_command": "readme-gen https://github.com/mithun50",
        "runtime_version": ">=3.10",
        "has_ci": True,
        "last_commit_date": "2026-03-13T10:00:00Z",
        "stars": 99,
        "package_manager": "pip",
    },
}

CONFIG = {
    "color": "A855F7",
    "gradient": "12,14,25,27",
    "header_type": "venom",
    "animation": "twinkling",
    "font": "JetBrains Mono",
    "stats_theme": "radical",
    "badge_style": "for-the-badge",
    "height": 200,
    "sections": ["header", "typing", "badges", "footer"],
    "icons": ["py", "docker", "git"],
    "llm": "gemini",
    "output": "./README.md",
    "output_length": "200-350",
    "tone": "Professional, personal, developer-native.",
}


class BuilderTestCase(unittest.TestCase):
    """Validate the deterministic URL builder outputs."""

    def setUp(self) -> None:
        """Create builders for profile and project contexts."""
        self.profile_builder = ReadmeBuilder(PROFILE_CONTEXT, CONFIG)
        self.project_builder = ReadmeBuilder(PROJECT_CONTEXT, CONFIG)

    def test_build_capsule_header_url(self) -> None:
        """Header URL should encode title and description."""
        url = self.profile_builder.build_capsule_header_url()
        self.assertIn("type=venom", url)
        self.assertIn("text=Mithun%20Gowda", url)
        self.assertIn("desc=Python%20engineer", url)

    def test_build_typing_svg_url(self) -> None:
        """Typing SVG URL should encode spaces with plus signs."""
        url = self.profile_builder.build_typing_svg_url()
        self.assertIn("font=JetBrains+Mono", url)
        self.assertIn("lines=Engineer", url)
        self.assertIn("Builds+developer+tooling+at+night.", url)

    def test_build_badge(self) -> None:
        """Badge URLs should follow the documented encoding rules."""
        url = self.profile_builder.build_badge("Last Commit", "2026-03-13", "A855F7", "git")
        self.assertIn("Last_Commit-2026--03--13-A855F7", url)
        self.assertIn("logo=git", url)

    def test_build_profile_badges(self) -> None:
        """Profile badges should include portfolio and PyPI when available."""
        badges = self.profile_builder.build_profile_badges()
        self.assertTrue(any("Portfolio" in badge for badge in badges))
        self.assertTrue(any("PyPI" in badge for badge in badges))

    def test_build_project_badges(self) -> None:
        """Project badges should include version and CLI platform."""
        badges = self.project_builder.build_project_badges()
        self.assertTrue(any("Version" in badge for badge in badges))
        self.assertTrue(any("Platform" in badge for badge in badges))

    def test_build_snake_url(self) -> None:
        """Snake URL should always target the profile repository."""
        self.assertEqual(
            self.project_builder.build_snake_url(),
            "https://raw.githubusercontent.com/mithun50/mithun50/output/github-snake-dark.svg",
        )

    def test_build_stats_urls(self) -> None:
        """Stats and graph URLs should carry theme and username state."""
        self.assertIn("theme=radical", self.profile_builder.build_stats_card_url())
        self.assertIn("layout=compact", self.profile_builder.build_top_langs_url())
        self.assertIn("currStreakLabel=A855F7", self.profile_builder.build_streak_url())
        self.assertIn("custom_title=Contribution+Activity", self.profile_builder.build_activity_graph_url())

    def test_build_summary_cards_urls(self) -> None:
        """Summary cards should return all three expected URLs."""
        urls = self.profile_builder.build_summary_cards_urls()
        self.assertEqual(len(urls), 3)
        self.assertTrue(all("mithun50" in url for url in urls))

    def test_build_trophies_and_quote_urls(self) -> None:
        """Trophies and quote widgets should point to the documented services."""
        self.assertIn("github-profile-trophy", self.profile_builder.build_trophies_url())
        self.assertIn("quotes-github-readme", self.profile_builder.build_quotes_url())

    def test_build_skillicons_url(self) -> None:
        """Skill icons should be comma-joined with the dark theme enabled."""
        url = self.profile_builder.build_skillicons_url(["py", "docker", "git"])
        self.assertEqual(url, "https://skillicons.dev/icons?i=py,docker,git&theme=dark")

    def test_build_views_counter_and_footer_urls(self) -> None:
        """Footer assets should include the selected color and gradient."""
        self.assertIn("color=A855F7", self.profile_builder.build_views_counter_url())
        self.assertIn("customColorList=12,14,25,27", self.profile_builder.build_footer_url())

    def test_build_language_and_social_badges(self) -> None:
        """Language and social badge collections should render Markdown snippets."""
        language_badges = self.profile_builder.build_language_badges()
        social_badges = self.profile_builder.build_social_badges()
        self.assertTrue(language_badges[0].startswith("![Python](https://img.shields.io/badge/"))
        self.assertTrue(social_badges[0].startswith("[![portfolio](https://img.shields.io/badge/"))


if __name__ == "__main__":
    unittest.main()
