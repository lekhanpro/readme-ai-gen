"""Unit tests for GitHub data fetching orchestration."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from readme_ai_gen.fetcher import GitHubFetcher


class FetcherTestCase(unittest.IsolatedAsyncioTestCase):
    """Validate fetcher orchestration and fallback behavior."""

    async def test_fetch_all_profile_mode_shapes_context(self) -> None:
        """Profile mode should aggregate repo, language, and social metadata."""
        fetcher = GitHubFetcher("https://github.com/mithun50")
        fetcher.fetch_user_profile = AsyncMock(
            return_value={
                "name": "Mithun Gowda",
                "bio": "Python engineer building tools.",
                "location": "India",
                "blog": "https://mithungowda.in",
                "company": "@openverse",
                "created_at": "2018-01-01T00:00:00Z",
                "avatar_url": "https://example.com/avatar.png",
                "public_repos": 5,
                "followers": 10,
                "following": 2,
            }
        )
        repos = [
            {"name": "one", "stargazers_count": 5, "topics": ["pypi"], "owner": {"login": "mithun50"}},
            {"name": "two", "stargazers_count": 3, "topics": [], "owner": {"login": "mithun50"}},
        ]
        fetcher.fetch_all_repos = AsyncMock(return_value=repos)
        fetcher.fetch_organizations = AsyncMock(return_value=[{"login": "openverse", "description": "OSS"}])
        fetcher.fetch_pinned_repos = AsyncMock(return_value=[{"name": "one", "stars": 5, "forks": 1, "language": "Python"}])
        fetcher.fetch_language_breakdown = AsyncMock(return_value={"Python": {"percent": 100.0, "proficiency": "Expert", "hex": "3776AB"}})
        fetcher.fetch_contribution_data = AsyncMock(
            return_value={
                "totalCommitContributions": 25,
                "totalPullRequestContributions": 7,
                "totalIssueContributions": 2,
            }
        )
        fetcher.fetch_social_links = AsyncMock(return_value={"portfolio": "mithungowda.in"})
        fetcher.fetch_existing_readme = AsyncMock(return_value="# Existing")
        fetcher.close = AsyncMock()

        context = await fetcher.fetch_all()

        self.assertEqual(context["mode"], "profile")
        self.assertEqual(context["display_name"], "Mithun Gowda")
        self.assertEqual(context["total_stars"], 8)
        self.assertTrue(context["has_pypi"])
        self.assertEqual(context["social_links"]["portfolio"], "mithungowda.in")

    async def test_fetch_all_project_mode_adds_project_context(self) -> None:
        """Project mode should include normalized repository metadata."""
        fetcher = GitHubFetcher("https://github.com/mithun50/readme-ai-gen")
        fetcher.fetch_user_profile = AsyncMock(
            return_value={
                "name": "Mithun Gowda",
                "bio": "Python engineer.",
                "location": "India",
                "created_at": "2018-01-01T00:00:00Z",
                "avatar_url": "https://example.com/avatar.png",
                "public_repos": 5,
                "followers": 10,
                "following": 2,
            }
        )
        fetcher.fetch_all_repos = AsyncMock(return_value=[])
        fetcher.fetch_organizations = AsyncMock(return_value=[])
        fetcher.fetch_pinned_repos = AsyncMock(return_value=[])
        fetcher.fetch_language_breakdown = AsyncMock(return_value={})
        fetcher.fetch_contribution_data = AsyncMock(return_value={})
        fetcher.fetch_social_links = AsyncMock(return_value={})
        fetcher.fetch_repo_metadata = AsyncMock(return_value={"name": "readme-ai-gen"})
        fetcher.fetch_repo_contents = AsyncMock(return_value={"tree_paths": []})
        fetcher._build_project_context = lambda metadata, contents: {"name": "readme-ai-gen", "type": "CLI Tool"}
        fetcher.fetch_existing_readme = AsyncMock(return_value=None)
        fetcher.close = AsyncMock()

        context = await fetcher.fetch_all()

        self.assertEqual(context["mode"], "project")
        self.assertEqual(context["project"]["type"], "CLI Tool")
        self.assertEqual(context["repo"], "readme-ai-gen")

    async def test_fetch_pinned_repos_falls_back_to_top_starred_repos(self) -> None:
        """Pinned repos should sort by stargazers when GraphQL is unavailable."""
        fetcher = GitHubFetcher("https://github.com/mithun50")
        fetcher._repos_cache = [
            {"name": "low", "stargazers_count": 1, "forks_count": 0, "owner": {"login": "mithun50"}},
            {"name": "high", "stargazers_count": 10, "forks_count": 1, "owner": {"login": "mithun50"}},
        ]
        result = await fetcher.fetch_pinned_repos()
        self.assertEqual(result[0]["name"], "high")

    async def test_fetch_contribution_data_without_token_returns_zeroes(self) -> None:
        """Contribution queries should degrade gracefully without GraphQL access."""
        fetcher = GitHubFetcher("https://github.com/mithun50")
        payload = await fetcher.fetch_contribution_data()
        self.assertEqual(payload["totalCommitContributions"], 0)
        await fetcher.close()


if __name__ == "__main__":
    unittest.main()
