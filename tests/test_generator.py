"""Unit tests for prompt assembly and provider selection."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from readme_ai_gen.generator import ReadmeGenerator, build_user_prompt


CONTEXT = {
    "mode": "project",
    "username": "mithun50",
    "display_name": "Mithun Gowda",
    "location": "Karnataka, India",
    "bio": "Python engineer and OSS builder.",
    "bio_parsed": {
        "roles": ["Engineer"],
        "stack_keywords": ["Python", "Fastapi"],
        "education": None,
        "ventures": ["openverse"],
        "fun_fact": "Builds docs after midnight.",
        "ask_me_about": ["Python", "APIs"],
    },
    "years_on_github": 7,
    "public_repos": 42,
    "followers": 50,
    "total_stars": 99,
    "total_commits": 1000,
    "total_prs": 120,
    "pinned_repos": [
        {"name": "readme-ai-gen", "description": "README generator", "stars": 99, "forks": 5, "language": "Python"}
    ],
    "orgs": [{"login": "openverse", "description": "OSS collective"}],
    "social_links": {"portfolio": "mithungowda.in"},
    "languages": {"Python": {"percent": 68.2, "proficiency": "Expert", "hex": "3776AB"}},
    "existing_readme": "Existing README body.",
    "project": {
        "name": "readme-ai-gen",
        "description": "Generate premium GitHub READMEs from any URL.",
        "type": "CLI Tool",
        "stack": ["Python", "Click", "Rich"],
        "license": "MIT",
        "version": "1.0.0",
        "install_command": "pip install readme-ai-gen",
        "run_command": "readme-gen https://github.com/mithun50/readme-ai-gen",
        "env_vars": ["GEMINI_API_KEY"],
        "has_docker": False,
        "has_ci": True,
        "last_commit_date": "2026-03-13",
        "tree": "├── readme_ai_gen\n└── tests",
    },
}

CONFIG = {
    "mode": "project",
    "theme": "purple",
    "color": "A855F7",
    "gradient": "12,14,25,27",
    "header_type": "venom",
    "animation": "twinkling",
    "font": "JetBrains Mono",
    "stats_theme": "radical",
    "badge_style": "for-the-badge",
    "height": 200,
    "sections": ["header", "typing", "badges", "about", "features", "footer"],
    "icons": ["py", "docker"],
    "llm": "gemini",
    "output": "./README.md",
    "output_length": "200-350",
    "tone": "Professional, personal, developer-native.",
}

BUILT_URLS = {
    "capsule_header_url": "https://capsule-render.vercel.app/api?type=venom",
    "capsule_footer_url": "https://capsule-render.vercel.app/api?type=waving",
    "typing_svg_url": "https://readme-typing-svg.demolab.com?font=JetBrains+Mono",
    "snake_url": "https://raw.githubusercontent.com/mithun50/mithun50/output/github-snake-dark.svg",
    "stats_card_url": "https://github-readme-stats.vercel.app/api?username=mithun50",
    "top_langs_url": "https://github-readme-stats.vercel.app/api/top-langs/?username=mithun50",
    "streak_url": "https://streak-stats.demolab.com/?user=mithun50",
    "activity_graph_url": "https://github-readme-activity-graph.vercel.app/graph?username=mithun50",
    "summary_cards_urls": [
        "https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=mithun50&theme=radical",
        "https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username=mithun50&theme=radical",
        "https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username=mithun50&theme=radical",
    ],
    "trophies_url": "https://github-profile-trophy.vercel.app/?username=mithun50",
    "quote_url": "https://quotes-github-readme.vercel.app/api?type=horizontal&theme=radical",
    "views_counter_url": "https://komarev.com/ghpvc/?username=mithun50",
    "language_badges": ["![Python](https://img.shields.io/badge/Python-Expert-3776AB)"],
    "skillicons_url": "https://skillicons.dev/icons?i=py,docker&theme=dark",
    "social_badges": ["[![portfolio](https://img.shields.io/badge/portfolio-portfolio-A855F7)](https://mithungowda.in)"],
    "profile_badges": ["![Repos](https://img.shields.io/badge/Repos-42-A855F7)"],
    "project_badges": ["![Version](https://img.shields.io/badge/Version-1.0.0-A855F7)"],
}


class GeneratorTestCase(unittest.IsolatedAsyncioTestCase):
    """Validate prompt assembly and generation behavior."""

    def test_build_user_prompt_contains_required_sections(self) -> None:
        """The dynamic user prompt should embed config, URLs, and project data."""
        prompt = build_user_prompt(CONTEXT, CONFIG, BUILT_URLS)
        self.assertIn("## GITHUB DATA", prompt)
        self.assertIn("PROJECT MODE DATA:", prompt)
        self.assertIn("https://capsule-render.vercel.app/api?type=venom", prompt)
        self.assertIn("### features (project mode only)", prompt)

    def test_build_system_prompt_formats_runtime_values(self) -> None:
        """The system prompt should include output length and tone."""
        generator = ReadmeGenerator(gemini_api_key="key")
        system_prompt = generator.build_system_prompt("200-350", "Professional")
        self.assertIn("Output length: 200-350 lines.", system_prompt)
        self.assertIn("Tone: Professional", system_prompt)

    async def test_generate_strips_code_fences(self) -> None:
        """The public generate method should clean fenced Markdown output."""
        generator = ReadmeGenerator(gemini_api_key="key")
        with patch.object(generator, "_generate_with_gemini", AsyncMock(return_value="```md\n# Title\n```")):
            output = await generator.generate(CONTEXT, CONFIG, BUILT_URLS, "gemini")
        self.assertEqual(output, "# Title")

    async def test_generate_requires_api_key(self) -> None:
        """Gemini generation should fail cleanly without credentials."""
        generator = ReadmeGenerator(gemini_api_key=None, openai_api_key=None)
        with self.assertRaisesRegex(Exception, "No API key found"):
            await generator.generate(CONTEXT, CONFIG, BUILT_URLS, "gemini")


if __name__ == "__main__":
    unittest.main()
