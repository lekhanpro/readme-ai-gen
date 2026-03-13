"""GitHub API data collection for readme-ai-gen."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import httpx

from .config import GITHUB_API, GITHUB_GRAPHQL, RAW_GITHUB, REQUEST_TIMEOUT, USER_AGENT
from .utils import (
    GitHubAPIError,
    build_repo_tree,
    decode_github_content,
    dedupe_preserve_order,
    detect_project_type,
    ensure_url_scheme,
    extract_env_vars,
    extract_social_links,
    infer_install_command,
    infer_language_proficiency,
    infer_run_command,
    parse_bio,
    parse_cargo_toml,
    parse_go_mod,
    parse_github_url,
    parse_make_targets,
    parse_package_json,
    parse_pyproject_text,
    parse_requirements,
    parse_setup_console_scripts,
    safe_excerpt,
    years_since,
)


class GitHubFetcher:
    """Fetch and normalize GitHub profile and repository data."""

    def __init__(self, url: str, token: str | None = None):
        """Parse the GitHub URL and initialize the async HTTP client."""
        username, repo, mode = parse_github_url(url)
        self.url = url.rstrip("/")
        self.username = username
        self.repo = repo
        self.mode = mode
        self.token = token
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.AsyncClient(headers=headers, timeout=REQUEST_TIMEOUT)
        self.status_callback: callable[[str], None] | None = None
        self._profile_cache: dict[str, Any] | None = None
        self._repos_cache: list[dict[str, Any]] | None = None
        self._repo_metadata_cache: dict[str, Any] | None = None

    async def __aenter__(self) -> "GitHubFetcher":
        """Return the fetcher for async context manager usage."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the async HTTP client when leaving a context manager."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()

    def _notify(self, message: str) -> None:
        """Emit progress updates when a callback is registered."""
        if self.status_callback:
            self.status_callback(message)

    async def _request_json(self, url: str, *, allow_404: bool = False) -> Any:
        """Perform a JSON request against the GitHub API."""
        try:
            response = await self.client.get(url)
        except httpx.RequestError as exc:
            raise GitHubAPIError("Could not reach GitHub API. Check your internet connection.") from exc

        if response.status_code == 404 and allow_404:
            return None
        if response.status_code == 404:
            target = f"{self.username}/{self.repo}" if self.repo else self.username
            raise GitHubAPIError(f"Repository/user not found at {self.url}", status_code=404)
        if response.status_code == 401:
            raise GitHubAPIError("Invalid GitHub token. Check GITHUB_TOKEN in .env", status_code=401)
        if response.status_code == 403:
            raise GitHubAPIError(
                "GitHub API rate limit exceeded. Add GITHUB_TOKEN to .env for 5000 req/hour",
                status_code=403,
            )
        if response.is_error:
            message = response.text.strip() or response.reason_phrase
            raise GitHubAPIError(message, status_code=response.status_code)
        return response.json()

    async def _request_text(self, url: str, *, allow_404: bool = False) -> str | None:
        """Perform a text request against a remote endpoint."""
        try:
            response = await self.client.get(url)
        except httpx.RequestError as exc:
            raise GitHubAPIError("Could not reach GitHub API. Check your internet connection.") from exc
        if response.status_code == 404 and allow_404:
            return None
        if response.is_error:
            raise GitHubAPIError(response.text.strip() or response.reason_phrase, status_code=response.status_code)
        return response.text

    async def _graphql(self, query: str) -> dict[str, Any]:
        """Execute a GitHub GraphQL query."""
        if not self.token:
            raise GitHubAPIError("GitHub GraphQL requires GITHUB_TOKEN.", status_code=401)
        try:
            response = await self.client.post(GITHUB_GRAPHQL, json={"query": query})
        except httpx.RequestError as exc:
            raise GitHubAPIError("Could not reach GitHub API. Check your internet connection.") from exc
        if response.status_code == 401:
            raise GitHubAPIError("Invalid GitHub token. Check GITHUB_TOKEN in .env", status_code=401)
        if response.status_code == 403:
            raise GitHubAPIError(
                "GitHub API rate limit exceeded. Add GITHUB_TOKEN to .env for 5000 req/hour",
                status_code=403,
            )
        payload = response.json()
        if payload.get("errors"):
            raise GitHubAPIError(payload["errors"][0].get("message", "GitHub GraphQL request failed."))
        return payload["data"]

    async def fetch_all(self) -> dict[str, Any]:
        """Fetch the full context dict consumed by the builder and generator."""
        try:
            self._notify("Fetching GitHub profile...")
            profile_task = asyncio.create_task(self.fetch_user_profile())
            self._notify("Fetching public repositories...")
            repos_task = asyncio.create_task(self.fetch_all_repos())
            self._notify("Fetching organizations...")
            orgs_task = asyncio.create_task(self.fetch_organizations())
            profile, repos, orgs = await asyncio.gather(profile_task, repos_task, orgs_task)
            self._profile_cache = profile
            self._repos_cache = repos

            self._notify("Fetching pinned repos...")
            pinned_repos = await self.fetch_pinned_repos()
            self._notify("Analyzing language breakdown...")
            languages = await self.fetch_language_breakdown()
            self._notify("Fetching contribution data...")
            contribution = await self.fetch_contribution_data()
            self._notify("Scanning social links...")
            social_links = await self.fetch_social_links()

            repo_metadata: dict[str, Any] | None = None
            repo_contents: dict[str, Any] | None = None
            project_context: dict[str, Any] | None = None
            if self.mode == "project":
                self._notify("Fetching repository metadata...")
                repo_metadata = await self.fetch_repo_metadata()
                self._notify("Scanning repository contents...")
                repo_contents = await self.fetch_repo_contents()
                project_context = self._build_project_context(repo_metadata, repo_contents)

            self._notify("Fetching existing README...")
            existing_readme = await self.fetch_existing_readme()

            total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
            top_repos = self._top_repositories(repos)
            all_topics = dedupe_preserve_order(
                topic
                for repo in repos
                for topic in (repo.get("topics") or [])
            )
            context = {
                "mode": self.mode,
                "username": self.username,
                "repo": self.repo,
                "display_name": profile.get("name") or self.username,
                "bio": profile.get("bio") or "",
                "bio_parsed": parse_bio(profile.get("bio")),
                "location": profile.get("location") or "",
                "blog_url": profile.get("blog") or None,
                "company": profile.get("company") or None,
                "years_on_github": years_since(profile.get("created_at")),
                "avatar_url": profile.get("avatar_url") or "",
                "public_repos": int(profile.get("public_repos") or 0),
                "followers": int(profile.get("followers") or 0),
                "following": int(profile.get("following") or 0),
                "total_stars": total_stars,
                "total_commits": contribution.get("totalCommitContributions", 0),
                "total_prs": contribution.get("totalPullRequestContributions", 0),
                "total_issues": contribution.get("totalIssueContributions", 0),
                "pinned_repos": pinned_repos,
                "top_repos": top_repos,
                "all_topics": all_topics,
                "languages": languages,
                "social_links": social_links,
                "orgs": orgs,
                "project": project_context,
                "existing_readme": existing_readme,
                "has_pypi": any("pypi" in (repo.get("name") or "").lower() or "pypi" in [topic.lower() for topic in repo.get("topics") or []] for repo in repos),
                "has_npm": any("npm" in (repo.get("name") or "").lower() or "npm" in [topic.lower() for topic in repo.get("topics") or []] for repo in repos),
                "repo_files": (repo_contents or {}).get("tree_paths", []),
                "repo_readme_excerpt": safe_excerpt(existing_readme),
            }
            return context
        finally:
            await self.close()

    async def fetch_user_profile(self) -> dict[str, Any]:
        """Fetch the user's public profile."""
        url = f"{GITHUB_API}/users/{self.username}"
        return await self._request_json(url)

    async def fetch_pinned_repos(self) -> list[dict[str, Any]]:
        """Fetch pinned repositories, falling back to top-starred repos when needed."""
        if not self._repos_cache:
            self._repos_cache = await self.fetch_all_repos()

        if self.token:
            query = f'''
            {{
              user(login: "{self.username}") {{
                pinnedItems(first: 6, types: REPOSITORY) {{
                  nodes {{
                    ... on Repository {{
                      name
                      description
                      url
                      stargazerCount
                      forkCount
                      primaryLanguage {{ name color }}
                      owner {{ login }}
                      repositoryTopics(first: 5) {{
                        nodes {{ topic {{ name }} }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            '''
            try:
                payload = await self._graphql(query)
                nodes = payload["user"]["pinnedItems"]["nodes"]
                return [
                    {
                        "name": node.get("name"),
                        "description": node.get("description") or "",
                        "url": node.get("url"),
                        "stars": int(node.get("stargazerCount") or 0),
                        "forks": int(node.get("forkCount") or 0),
                        "language": (node.get("primaryLanguage") or {}).get("name"),
                        "topics": [item["topic"]["name"] for item in node.get("repositoryTopics", {}).get("nodes", [])],
                        "owner": (node.get("owner") or {}).get("login", self.username),
                    }
                    for node in nodes
                ]
            except GitHubAPIError:
                pass

        return [
            {
                "name": repo.get("name"),
                "description": repo.get("description") or "",
                "url": repo.get("html_url"),
                "stars": int(repo.get("stargazers_count") or 0),
                "forks": int(repo.get("forks_count") or 0),
                "language": repo.get("language"),
                "topics": repo.get("topics") or [],
                "owner": ((repo.get("owner") or {}).get("login") or self.username),
            }
            for repo in self._top_repositories(self._repos_cache)
        ]

    async def fetch_all_repos(self) -> list[dict[str, Any]]:
        """Fetch up to 100 public repositories for the user."""
        url = f"{GITHUB_API}/users/{self.username}/repos?per_page=100&sort=updated"
        return await self._request_json(url)

    async def fetch_language_breakdown(self) -> dict[str, dict[str, Any]]:
        """Aggregate language bytes and proficiency across the user's top repositories."""
        if not self._repos_cache:
            self._repos_cache = await self.fetch_all_repos()
        repos = self._top_repositories(self._repos_cache, limit=10)
        if not repos:
            return {}

        aggregate_bytes: dict[str, int] = {}
        repo_presence: dict[str, int] = {}
        for repo in repos:
            owner = (repo.get("owner") or {}).get("login", self.username)
            repo_name = repo.get("name")
            if not repo_name:
                continue
            url = f"{GITHUB_API}/repos/{owner}/{repo_name}/languages"
            payload = await self._request_json(url, allow_404=True) or {}
            for language, byte_count in payload.items():
                aggregate_bytes[language] = aggregate_bytes.get(language, 0) + int(byte_count)
            for language in payload:
                repo_presence[language] = repo_presence.get(language, 0) + 1

        total_bytes = sum(aggregate_bytes.values()) or 1
        total_repos = max(len(repos), 1)
        breakdown: dict[str, dict[str, Any]] = {}
        for language, byte_count in sorted(aggregate_bytes.items(), key=lambda item: item[1], reverse=True):
            percent = round((byte_count / total_bytes) * 100, 1)
            presence_percent = (repo_presence.get(language, 0) / total_repos) * 100
            breakdown[language] = {
                "percent": percent,
                "proficiency": infer_language_proficiency(presence_percent),
                "hex": self._language_hex(language),
            }
        return breakdown

    async def fetch_contribution_data(self) -> dict[str, Any]:
        """Fetch contribution statistics from GitHub GraphQL."""
        if not self.token:
            return {
                "totalCommitContributions": 0,
                "totalPullRequestContributions": 0,
                "totalIssueContributions": 0,
                "totalRepositoryContributions": 0,
                "contributionCalendar": {"totalContributions": 0},
            }
        query = f'''
        {{
          user(login: "{self.username}") {{
            contributionsCollection {{
              totalCommitContributions
              totalPullRequestContributions
              totalIssueContributions
              totalRepositoryContributions
              contributionCalendar {{
                totalContributions
              }}
            }}
          }}
        }}
        '''
        try:
            payload = await self._graphql(query)
            return payload["user"]["contributionsCollection"]
        except GitHubAPIError:
            return {
                "totalCommitContributions": 0,
                "totalPullRequestContributions": 0,
                "totalIssueContributions": 0,
                "totalRepositoryContributions": 0,
                "contributionCalendar": {"totalContributions": 0},
            }

    async def fetch_organizations(self) -> list[dict[str, Any]]:
        """Fetch organizations the user belongs to."""
        url = f"{GITHUB_API}/users/{self.username}/orgs"
        payload = await self._request_json(url, allow_404=True) or []
        return [
            {
                "login": org.get("login"),
                "description": org.get("description") or "",
                "avatar_url": org.get("avatar_url") or "",
            }
            for org in payload
        ]

    async def fetch_social_links(self) -> dict[str, str]:
        """Extract social links from the fetched profile payload."""
        if not self._profile_cache:
            self._profile_cache = await self.fetch_user_profile()
        return extract_social_links(self._profile_cache)

    async def fetch_repo_contents(self) -> dict[str, Any]:
        """Fetch repository file contents and a shallow directory tree for project mode."""
        if self.mode != "project" or not self.repo:
            return {}
        metadata = self._repo_metadata_cache or await self.fetch_repo_metadata()
        branch = metadata.get("default_branch") or "main"
        root_url = f"{GITHUB_API}/repos/{self.username}/{self.repo}/contents?ref={branch}"
        root_listing = await self._request_json(root_url)
        root_entries = {entry["name"].lower(): entry for entry in root_listing}
        known_paths = [
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            "Makefile",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
        ]
        files: dict[str, str | None] = {}
        for path in known_paths:
            entry = root_entries.get(path.lower())
            files[path] = await self._fetch_repo_file(entry["path"], branch) if entry else None

        workflows_url = f"{GITHUB_API}/repos/{self.username}/{self.repo}/contents/.github/workflows?ref={branch}"
        workflows = await self._request_json(workflows_url, allow_404=True) or []
        tree_paths = await self._walk_contents("", branch, depth=0, max_depth=2)
        return {
            "files": files,
            "has_ci": any(item.get("name", "").endswith((".yml", ".yaml")) for item in workflows),
            "tree_paths": dedupe_preserve_order(tree_paths),
        }

    async def fetch_repo_metadata(self) -> dict[str, Any]:
        """Fetch repository metadata, latest release, and last commit date."""
        if self.mode != "project" or not self.repo:
            return {}
        repo_url = f"{GITHUB_API}/repos/{self.username}/{self.repo}"
        payload = await self._request_json(repo_url)
        release_url = f"{GITHUB_API}/repos/{self.username}/{self.repo}/releases/latest"
        latest_release = await self._request_json(release_url, allow_404=True) or {}
        commits_url = f"{GITHUB_API}/repos/{self.username}/{self.repo}/commits?per_page=1"
        commits = await self._request_json(commits_url, allow_404=True) or []
        payload["latest_release"] = latest_release.get("tag_name")
        payload["last_commit_date"] = (
            commits[0].get("commit", {}).get("author", {}).get("date")
            if commits
            else None
        )
        self._repo_metadata_cache = payload
        return payload

    async def fetch_existing_readme(self) -> str | None:
        """Fetch the existing README from raw.githubusercontent.com when available."""
        candidates: list[tuple[str, str]] = []
        if self.mode == "project" and self.repo:
            metadata = self._repo_metadata_cache or await self.fetch_repo_metadata()
            branches = [metadata.get("default_branch") or "main", "main", "master"]
            candidates = [(self.repo, branch) for branch in dedupe_preserve_order(branches)]
        else:
            candidates = [(self.username, branch) for branch in ["main", "master"]]

        for repo_name, branch in candidates:
            raw_url = f"{RAW_GITHUB}/{self.username}/{repo_name}/{branch}/README.md"
            text = await self._request_text(raw_url, allow_404=True)
            if text:
                return text
        return None

    async def _fetch_repo_file(self, path: str, branch: str) -> str | None:
        """Fetch and decode a single repository file from the contents API."""
        url = f"{GITHUB_API}/repos/{self.username}/{self.repo}/contents/{quote(path, safe='/')}?ref={branch}"
        payload = await self._request_json(url, allow_404=True)
        if not payload or isinstance(payload, list):
            return None
        return decode_github_content(payload)

    async def _walk_contents(self, path: str, branch: str, *, depth: int, max_depth: int) -> list[str]:
        """Walk repository contents up to a bounded depth for structure rendering."""
        suffix = f"/{quote(path, safe='/')}" if path else ""
        url = f"{GITHUB_API}/repos/{self.username}/{self.repo}/contents{suffix}?ref={branch}"
        payload = await self._request_json(url, allow_404=True)
        if not payload:
            return []
        if isinstance(payload, dict):
            return [payload.get("path", path)]
        output: list[str] = []
        for item in payload:
            item_path = item.get("path")
            if not item_path:
                continue
            output.append(item_path)
            if item.get("type") == "dir" and depth < max_depth:
                output.extend(await self._walk_contents(item_path, branch, depth=depth + 1, max_depth=max_depth))
        return output

    def _build_project_context(self, metadata: dict[str, Any], repo_contents: dict[str, Any]) -> dict[str, Any]:
        """Normalize project-specific metadata into the shared context format."""
        files = repo_contents.get("files") or {}
        package_json = parse_package_json(files["package.json"]) if files.get("package.json") else {}
        pyproject = parse_pyproject_text(files["pyproject.toml"]) if files.get("pyproject.toml") else {}
        cargo = parse_cargo_toml(files["Cargo.toml"]) if files.get("Cargo.toml") else {}
        go_mod = parse_go_mod(files["go.mod"]) if files.get("go.mod") else {}
        requirements = parse_requirements(files["requirements.txt"]) if files.get("requirements.txt") else []
        entry_points = parse_setup_console_scripts(files["setup.py"]) if files.get("setup.py") else []
        make_targets = parse_make_targets(files["Makefile"]) if files.get("Makefile") else []
        env_vars = extract_env_vars(files[".env.example"]) if files.get(".env.example") else []

        project_data = {
            "name": package_json.get("name")
            or (pyproject.get("project") or {}).get("name")
            or (cargo.get("package") or {}).get("name")
            or metadata.get("name")
            or self.repo,
            "package_json": package_json,
            "pyproject": pyproject,
            "cargo": cargo,
            "go_mod": go_mod,
            "requirements": requirements,
            "setup_py": files.get("setup.py"),
            "entry_points": entry_points,
            "make_targets": make_targets,
            "files": repo_contents.get("tree_paths") or [],
        }
        project_type = detect_project_type(project_data)
        project_data["type"] = project_type

        dependencies = dedupe_preserve_order(
            list(package_json.get("dependencies", {}).keys())
            + list(package_json.get("devDependencies", {}).keys())
            + requirements
            + [dep.split()[0] for dep in (pyproject.get("project") or {}).get("dependencies", [])]
        )
        stack = dedupe_preserve_order(
            [metadata.get("language")] + dependencies + (metadata.get("topics") or [])
        )
        runtime_version = (
            ((pyproject.get("project") or {}).get("requires-python"))
            or ((package_json.get("engines") or {}).get("node"))
            or go_mod.get("go_version")
            or ((cargo.get("package") or {}).get("rust-version"))
        )
        version = (
            metadata.get("latest_release")
            or package_json.get("version")
            or (pyproject.get("project") or {}).get("version")
            or (cargo.get("package") or {}).get("version")
        )
        license_name = (metadata.get("license") or {}).get("name") or "No license specified"
        description = (
            metadata.get("description")
            or package_json.get("description")
            or (pyproject.get("project") or {}).get("description")
            or (cargo.get("package") or {}).get("description")
            or ""
        )
        return {
            "name": metadata.get("name") or self.repo,
            "description": description,
            "version": version,
            "license": license_name,
            "topics": metadata.get("topics") or [],
            "type": project_type,
            "stack": [item for item in stack if item][:12],
            "install_command": infer_install_command(project_data),
            "run_command": infer_run_command(project_data),
            "env_vars": env_vars,
            "has_docker": bool(files.get("Dockerfile") or files.get("docker-compose.yml")),
            "has_ci": bool(repo_contents.get("has_ci")),
            "open_issues": int(metadata.get("open_issues_count") or 0),
            "watchers": int(metadata.get("watchers_count") or 0),
            "last_commit_date": metadata.get("last_commit_date") or "",
            "stars": int(metadata.get("stargazers_count") or 0),
            "default_branch": metadata.get("default_branch") or "main",
            "runtime_version": runtime_version,
            "package_manager": self._package_manager(project_data),
            "tree": build_repo_tree(repo_contents.get("tree_paths") or []),
            "entry_points": entry_points,
        }

    def _top_repositories(self, repos: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
        """Return repositories sorted by stargazers count."""
        return sorted(repos, key=lambda repo: int(repo.get("stargazers_count") or 0), reverse=True)[:limit]

    def _language_hex(self, language: str) -> str:
        """Return a shields-friendly hex color for a language name."""
        from .config import LANGUAGE_COLORS

        return LANGUAGE_COLORS.get(language, "A855F7")

    def _package_manager(self, project_data: dict[str, Any]) -> str | None:
        """Infer the dominant package manager for project mode."""
        if project_data.get("package_json"):
            return "npm"
        if project_data.get("pyproject") or project_data.get("requirements") or project_data.get("setup_py"):
            return "pip"
        if project_data.get("cargo"):
            return "cargo"
        if project_data.get("go_mod"):
            return "go"
        return None
