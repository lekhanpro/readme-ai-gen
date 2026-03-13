"""Utility helpers for readme-ai-gen."""

from __future__ import annotations

import base64
import json
import re
import tomllib
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import quote, quote_plus, urlparse

from .config import (
    ALL_ICONS,
    DEFAULT_THEME,
    LANGUAGE_COLORS,
    LANGUAGE_ICON_MAP,
    PROFILE_SECTIONS_DEFAULT,
    PROJECT_SECTIONS_DEFAULT,
    SECTION_ORDER,
    TECH_KEYWORDS,
    THEMES,
)


class ReadmeGenError(Exception):
    """Base exception for the project."""


class URLParseError(ReadmeGenError):
    """Raised when a GitHub URL cannot be parsed."""


class GitHubAPIError(ReadmeGenError):
    """Raised when a GitHub API request fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LLMError(ReadmeGenError):
    """Raised when the LLM call fails."""


class DependencyError(ReadmeGenError):
    """Raised when an optional runtime dependency is unavailable."""


def parse_github_url(url: str) -> tuple[str, str | None, str]:
    """Parse a GitHub profile or repository URL into username, repo, and mode."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in {"github.com", "www.github.com"}:
        raise URLParseError("Could not parse GitHub URL. Expected: https://github.com/username")

    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        raise URLParseError("Could not parse GitHub URL. Expected: https://github.com/username")

    username = parts[0]
    if len(parts) == 1:
        return username, None, "profile"

    repo = parts[1].removesuffix(".git")
    if not repo:
        raise URLParseError("For project mode, use: https://github.com/username/repo-name")
    return username, repo, "project"


def normalize_hex_color(color: str | None) -> str:
    """Normalize a theme color or hex string into an uppercase six-character hex value."""
    if not color:
        return THEMES[DEFAULT_THEME]["hex"]
    candidate = color.strip().lower().lstrip("#")
    if candidate in THEMES:
        return THEMES[candidate]["hex"]
    if re.fullmatch(r"[0-9a-fA-F]{6}", candidate):
        return candidate.upper()
    raise ValueError(f"Invalid color value: {color}")


def hex_to_rgb_string(hex_color: str) -> str:
    """Convert a hex color into an RGB string."""
    normalized = normalize_hex_color(hex_color)
    channels = [str(int(normalized[index:index + 2], 16)) for index in range(0, 6, 2)]
    return ",".join(channels)


def resolve_theme(color: str | None) -> dict[str, str]:
    """Resolve a named theme or custom hex value into a full theme dictionary."""
    if not color:
        theme = THEMES[DEFAULT_THEME].copy()
        theme["name"] = DEFAULT_THEME
        return theme

    candidate = color.strip().lower().lstrip("#")
    if candidate in THEMES:
        theme = THEMES[candidate].copy()
        theme["name"] = candidate
        return theme

    normalized = normalize_hex_color(candidate)
    return {
        "name": "custom",
        "hex": normalized,
        "rgb": hex_to_rgb_string(normalized),
        "gradient": THEMES[DEFAULT_THEME]["gradient"],
    }


def encode_capsule_text(text: str) -> str:
    """Encode text for capsule-render URLs."""
    return quote(text, safe="")


def encode_typing_font(font: str) -> str:
    """Encode a font name for the typing SVG service."""
    return quote_plus(font.replace("+", " "))


def encode_typing_line(text: str) -> str:
    """Encode a line for the typing SVG service."""
    return quote_plus(text)


def encode_badge_fragment(text: str, *, label: bool = False) -> str:
    """Encode a badge label or value for shields.io."""
    encoded = text.replace("_", "__") if label else text
    encoded = encoded.replace("-", "--")
    encoded = encoded.replace(" ", "_")
    return quote(encoded, safe="_")


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    """Return a list with duplicates removed while preserving order."""
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def years_since(date_string: str | None) -> int:
    """Return the number of full years since the provided ISO timestamp."""
    if not date_string:
        return 0
    created = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return max(now.year - created.year - ((now.month, now.day) < (created.month, created.day)), 0)


def slugify_identifier(value: str) -> str:
    """Convert arbitrary text into a JavaScript-safe identifier."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().split()
    if not cleaned:
        return "profile"
    head, *tail = cleaned
    return head.lower() + "".join(token.title() for token in tail)


def ensure_url_scheme(value: str) -> str:
    """Ensure a URL string includes an HTTP scheme."""
    if value.startswith(("http://", "https://", "mailto:")):
        return value
    return f"https://{value}"


def parse_bio(bio: str | None) -> dict[str, Any]:
    """Parse common profile signals out of a GitHub bio."""
    text = (bio or "").strip()
    lowered = text.lower()
    roles = [
        role.title()
        for role in [
            "developer",
            "engineer",
            "founder",
            "student",
            "researcher",
            "maintainer",
            "designer",
            "consultant",
            "architect",
            "creator",
            "hacker",
        ]
        if role in lowered
    ]
    stack_keywords = [keyword.title() for keyword in TECH_KEYWORDS if keyword in lowered]

    education_match = re.search(
        r"((?:student|studying|alumn(?:us|a)|b\.tech|m\.tech|phd|msc|bs|ms)(?:[^|,.;])*)",
        text,
        re.IGNORECASE,
    )
    education = {"summary": education_match.group(1).strip()} if education_match else None

    ventures = dedupe_preserve_order(re.findall(r"@([A-Za-z0-9_-]+)", text))

    ask_me_about: list[str] = []
    ask_match = re.search(r"ask me about[:\s]+(.+?)(?:[.!]|$)", text, re.IGNORECASE)
    if ask_match:
        ask_me_about = [
            item.strip().title()
            for item in re.split(r",|/| and |\|", ask_match.group(1))
            if item.strip()
        ]

    fun_fact = None
    for segment in re.split(r"[.!?]", text):
        candidate = segment.strip()
        if candidate and any(token in candidate.lower() for token in ["coffee", "music", "build", "learn", "open source", "ship"]):
            fun_fact = candidate
            break

    return {
        "roles": dedupe_preserve_order(roles),
        "stack_keywords": dedupe_preserve_order(stack_keywords),
        "education": education,
        "ventures": ventures,
        "fun_fact": fun_fact,
        "ask_me_about": dedupe_preserve_order(ask_me_about),
    }


def extract_social_links(profile: Mapping[str, Any]) -> dict[str, str]:
    """Extract social links from GitHub profile fields and bio text."""
    links: dict[str, str] = {}
    blog = str(profile.get("blog") or "").strip()
    bio = str(profile.get("bio") or "")
    email = str(profile.get("email") or "").strip()
    if blog:
        parsed = urlparse(ensure_url_scheme(blog))
        portfolio = parsed.netloc + parsed.path if parsed.netloc else blog
        links["portfolio"] = portfolio.strip("/")
    twitter_username = str(profile.get("twitter_username") or "").strip()
    if twitter_username:
        links["twitter"] = f"https://x.com/{twitter_username.lstrip('@')}"
    if email:
        links["email"] = f"mailto:{email}"

    patterns = {
        "linkedin": r"(https?://(?:www\.)?linkedin\.com/[^\s)]+)",
        "youtube": r"(https?://(?:www\.)?youtube\.com/[^\s)]+)",
        "discord": r"(https?://discord\.gg/[^\s)]+)",
        "instagram": r"(https?://(?:www\.)?instagram\.com/[^\s)]+)",
        "pypi": r"(https?://(?:www\.)?pypi\.org/[^\s)]+)",
        "npm": r"(https?://(?:www\.)?npmjs\.com/[^\s)]+)",
        "orcid": r"(https?://(?:www\.)?orcid\.org/[^\s)]+)",
        "telegram": r"(https?://t\.me/[^\s)]+)",
    }
    haystack = " ".join(filter(None, [bio, blog]))
    for platform, pattern in patterns.items():
        match = re.search(pattern, haystack, re.IGNORECASE)
        if match:
            links[platform] = match.group(1)
    return links


def infer_language_proficiency(repo_presence_percent: float) -> str:
    """Convert a language presence percentage into a proficiency label."""
    if repo_presence_percent > 40:
        return "Expert"
    if 20 <= repo_presence_percent <= 40:
        return "Advanced"
    if 5 <= repo_presence_percent < 20:
        return "Intermediate"
    return "Learning"


def parse_csv_list(value: str | None) -> list[str]:
    """Split a comma-separated string into a cleaned list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def count_lines(text: str) -> int:
    """Return the number of lines in a string."""
    return len(text.splitlines())


def strip_markdown_fences(text: str) -> str:
    """Remove wrapping Markdown code fences from model output."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return stripped


def decode_github_content(payload: Mapping[str, Any]) -> str:
    """Decode GitHub contents API payloads into plain text."""
    content = str(payload.get("content") or "")
    if payload.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return content


def extract_env_vars(text: str) -> list[str]:
    """Extract environment variable names from a .env.example file."""
    return dedupe_preserve_order(re.findall(r"^([A-Z][A-Z0-9_]+)=", text, re.MULTILINE))


def parse_requirements(text: str) -> list[str]:
    """Parse a requirements.txt style dependency list."""
    dependencies: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        name = re.split(r"[<>=!~\[]", cleaned, maxsplit=1)[0].strip()
        if name:
            dependencies.append(name)
    return dependencies


def parse_setup_console_scripts(text: str) -> list[str]:
    """Extract console script entry points from setup.py text."""
    match = re.search(r"console_scripts\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))


def parse_make_targets(text: str) -> list[str]:
    """Extract named Makefile targets."""
    return dedupe_preserve_order(re.findall(r"^([A-Za-z0-9_.-]+):", text, re.MULTILINE))


def parse_package_json(text: str) -> dict[str, Any]:
    """Parse package.json text safely."""
    return json.loads(text)


def parse_pyproject_text(text: str) -> dict[str, Any]:
    """Parse pyproject.toml text safely."""
    return tomllib.loads(text)


def parse_cargo_toml(text: str) -> dict[str, Any]:
    """Parse Cargo.toml text safely."""
    return tomllib.loads(text)


def parse_go_mod(text: str) -> dict[str, str | None]:
    """Extract module metadata from go.mod text."""
    module_match = re.search(r"^module\s+(.+)$", text, re.MULTILINE)
    version_match = re.search(r"^go\s+(.+)$", text, re.MULTILINE)
    return {
        "module": module_match.group(1).strip() if module_match else None,
        "go_version": version_match.group(1).strip() if version_match else None,
    }


def detect_project_type(project_data: Mapping[str, Any]) -> str:
    """Infer a high-level project type from parsed repository metadata."""
    package_json = project_data.get("package_json") or {}
    pyproject = project_data.get("pyproject") or {}
    entry_points = project_data.get("entry_points") or []
    files = {path.lower() for path in project_data.get("files", [])}
    dependencies = {
        dependency.lower()
        for dependency in (
            list(package_json.get("dependencies", {}).keys())
            + list(package_json.get("devDependencies", {}).keys())
            + project_data.get("requirements", [])
            + list((pyproject.get("project") or {}).get("dependencies", []))
        )
    }

    if entry_points or package_json.get("bin"):
        return "CLI Tool"
    if dependencies & {"react", "next", "nextjs", "vue", "angular", "svelte"} and package_json.get("scripts", {}).get("start"):
        return "Web App"
    if dependencies & {"fastapi", "flask", "django", "express"}:
        return "API Server"
    if dependencies & {"pandas", "numpy", "scikit-learn", "sklearn", "torch", "tensorflow", "jupyter"}:
        return "Data Science"
    if dependencies & {"flutter", "react-native", "kotlin", "swift"} or any(token in " ".join(files) for token in ["android", "ios"]):
        return "Mobile App"
    return "Library/SDK"


def infer_install_command(project_data: Mapping[str, Any]) -> str:
    """Infer an installation command from parsed repository metadata."""
    project_type = str(project_data.get("type") or "")
    package_json = project_data.get("package_json") or {}
    pyproject = project_data.get("pyproject") or {}
    cargo = project_data.get("cargo") or {}
    go_mod = project_data.get("go_mod") or {}

    if package_json:
        package_name = package_json.get("name") or project_data.get("name") or "package-name"
        if project_type == "CLI Tool" and package_json.get("bin"):
            return f"npm install -g {package_name}"
        return "npm install"
    if pyproject or project_data.get("requirements") or project_data.get("setup_py"):
        project_meta = pyproject.get("project") or {}
        package_name = project_meta.get("name") or project_data.get("name")
        if project_type == "CLI Tool" and package_name:
            return f"pip install {package_name}"
        if project_data.get("requirements"):
            return "pip install -r requirements.txt"
        return "pip install -e ."
    if cargo:
        crate_name = (cargo.get("package") or {}).get("name")
        return f"cargo install {crate_name}" if crate_name else "cargo build --release"
    if go_mod.get("module"):
        return f"go install {go_mod['module']}@latest"
    return "See project documentation for installation steps"


def infer_run_command(project_data: Mapping[str, Any]) -> str:
    """Infer a run command from parsed repository metadata."""
    package_json = project_data.get("package_json") or {}
    scripts = package_json.get("scripts", {})
    if scripts.get("dev"):
        return "npm run dev"
    if scripts.get("start"):
        return "npm start"
    if scripts.get("build") and project_data.get("type") == "Web App":
        return "npm run build"
    entry_points = project_data.get("entry_points") or []
    if entry_points:
        return entry_points[0].split("=")[0].strip()
    if project_data.get("pyproject") or project_data.get("requirements") or project_data.get("setup_py"):
        return "python -m <module>"
    if project_data.get("cargo"):
        return "cargo run"
    if project_data.get("go_mod"):
        return "go run ."
    make_targets = project_data.get("make_targets") or []
    if "run" in make_targets:
        return "make run"
    return "See project documentation for usage details"


def detect_icons_from_context(context: Mapping[str, Any]) -> list[str]:
    """Infer a reasonable default icon set from fetched profile and project data."""
    icons: list[str] = []
    for language in (context.get("languages") or {}).keys():
        icon = LANGUAGE_ICON_MAP.get(language)
        if icon:
            icons.append(icon)
    project = context.get("project") or {}
    for item in project.get("stack", []):
        token = str(item).lower().replace(" ", "")
        for icon in ALL_ICONS:
            if icon in token or token in icon:
                icons.append(icon)
                break
    for keyword in context.get("bio_parsed", {}).get("stack_keywords", []):
        token = keyword.lower().replace(" ", "")
        for icon in ALL_ICONS:
            if icon in token or token in icon:
                icons.append(icon)
                break
    icons.extend(["git", "github"])
    return dedupe_preserve_order([icon for icon in icons if icon in ALL_ICONS])[:12]


def get_default_sections(mode: str) -> list[str]:
    """Return the default section list for a generation mode."""
    if mode == "project":
        return PROJECT_SECTIONS_DEFAULT.copy()
    return PROFILE_SECTIONS_DEFAULT.copy()


def order_sections(sections: Iterable[str]) -> list[str]:
    """Sort selected sections into the documented output order."""
    selected = set(sections)
    return [section for section in SECTION_ORDER if section in selected]


def build_repo_tree(paths: Iterable[str], max_depth: int = 3) -> str:
    """Render a repository tree from a list of POSIX paths."""
    skip_parts = {"node_modules", ".git", "__pycache__", "dist", ".next", ".cache", "venv"}
    tree: dict[str, Any] = {}

    for raw_path in paths:
        pure = PurePosixPath(raw_path)
        parts = [part for part in pure.parts if part not in skip_parts][:max_depth]
        if not parts:
            continue
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    comments = {
        "cli.py": "CLI entry point",
        "config.py": "shared defaults and theme config",
        "fetcher.py": "GitHub data collection",
        "generator.py": "LLM prompt and API integration",
        "renderer.py": "fetch + build + generation orchestration",
        "tests": "test suite",
        "pyproject.toml": "packaging and dependency metadata",
        ".github": "automation and workflow files",
    }

    def render(node: dict[str, Any], prefix: str = "") -> list[str]:
        lines: list[str] = []
        items = sorted(node.items(), key=lambda item: (bool(item[1]), item[0].lower()))
        for index, (name, child) in enumerate(items):
            connector = "└──" if index == len(items) - 1 else "├──"
            line = f"{prefix}{connector} {name}"
            if name in comments:
                line += f"  # {comments[name]}"
            lines.append(line)
            if child:
                extension = "    " if index == len(items) - 1 else "│   "
                lines.extend(render(child, prefix + extension))
        return lines

    return "\n".join(render(tree))


def safe_excerpt(text: str | None, limit: int = 1200) -> str:
    """Return a trimmed excerpt for prompt context."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
