"""README URL and badge builder for readme-ai-gen."""

from __future__ import annotations

from typing import Any

from .config import LANGUAGE_ICON_MAP, SOCIAL_LOGO_MAP
from .utils import (
    encode_badge_fragment,
    encode_capsule_text,
    encode_typing_font,
    encode_typing_line,
    ensure_url_scheme,
    normalize_hex_color,
)


class ReadmeBuilder:
    """Build all external asset URLs used by the README generator."""

    def __init__(self, context: dict[str, Any], config: dict[str, Any]):
        """Store the fetched context and normalized configuration."""
        self.ctx = context
        self.cfg = config
        self.hex = normalize_hex_color(config["color"])
        self.gradient = config["gradient"]
        self.badge_style = config["badge_style"]
        self.stats_theme = config["stats_theme"]

    def build_capsule_header_url(self) -> str:
        """Build the capsule-render header URL."""
        text = self.ctx["display_name"] if self.ctx["mode"] == "profile" else self.ctx["project"]["name"]
        desc = self.ctx["bio"] if self.ctx["mode"] == "profile" else self.ctx["project"]["description"]
        return (
            "https://capsule-render.vercel.app/api"
            f"?type={self.cfg['header_type']}"
            f"&color=gradient&customColorList={self.gradient}"
            f"&height={self.cfg['height']}&section=header"
            f"&text={encode_capsule_text(text)}"
            "&fontSize=60&fontColor=fff"
            f"&animation={self.cfg['animation']}"
            "&fontAlignY=35"
            f"&desc={encode_capsule_text(desc or self.ctx['username'])}"
            "&descSize=18&descAlignY=55"
        )

    def build_typing_svg_url(self) -> str:
        """Build the typing SVG URL."""
        lines = self._typing_lines()
        joined_lines = ";".join(encode_typing_line(line) for line in lines)
        return (
            "https://readme-typing-svg.demolab.com"
            f"?font={encode_typing_font(self.cfg['font'])}"
            "&weight=600&size=22&duration=3000&pause=1000"
            f"&color={self.hex}"
            "&center=true&vCenter=true&multiline=true&repeat=true"
            f"&width=800&height=80&lines={joined_lines}"
        )

    def build_badge(self, label: str, value: str, hex: str, logo: str = "") -> str:
        """Build a single shields.io badge URL."""
        label_part = encode_badge_fragment(label, label=True)
        value_part = encode_badge_fragment(value)
        url = (
            f"https://img.shields.io/badge/{label_part}-{value_part}-{normalize_hex_color(hex)}"
            f"?style={self.badge_style}"
        )
        if logo:
            url += f"&logo={logo}&logoColor=white"
        url += "&labelColor=1a1a2e"
        return url

    def build_profile_badges(self) -> list[str]:
        """Build profile-specific badges as Markdown images."""
        badges = [
            ("Repos", str(self.ctx["public_repos"]), self.hex, "github"),
            ("Stars", str(self.ctx["total_stars"]), self.hex, "github"),
            ("Followers", str(self.ctx["followers"]), self.hex, "github"),
            ("Collaborate", "Open", self.hex, "handshake"),
        ]
        if self.ctx.get("location"):
            badges.append(("Location", self.ctx["location"], self.hex, "googlemaps"))
        if self.ctx.get("social_links", {}).get("portfolio"):
            badges.append(("Portfolio", "Available", self.hex, "safari"))
        if self.ctx.get("has_pypi"):
            badges.append(("PyPI", "Active", "3775A9", "pypi"))
        if self.ctx.get("has_npm"):
            badges.append(("npm", "Active", "CB3837", "npm"))
        return [f"![{label}]({self.build_badge(label, value, color, logo)})" for label, value, color, logo in badges]

    def build_project_badges(self) -> list[str]:
        """Build project-specific badges as Markdown images."""
        project = self.ctx["project"]
        badges: list[tuple[str, str, str, str]] = []
        if project.get("version"):
            badges.append(("Version", str(project["version"]), self.hex, "semver"))
        badges.append(("License", project["license"], self.hex, "opensourceinitiative"))
        if project.get("has_ci"):
            badges.append(("Build", "CI", self.hex, "githubactions"))
        if project.get("runtime_version"):
            runtime_label = self._runtime_label(project)
            badges.append((runtime_label, str(project["runtime_version"]), self.hex, runtime_label.lower()))
        if project.get("last_commit_date"):
            badges.append(("Last Commit", str(project["last_commit_date"])[:10], self.hex, "git"))
        badges.append(("Stars", str(project.get("stars", 0)), self.hex, "github"))
        if project.get("type") == "CLI Tool":
            badges.append(("Platform", "CLI", self.hex, "windowsterminal"))
        return [f"![{label}]({self.build_badge(label, value, color, logo)})" for label, value, color, logo in badges]

    def build_snake_url(self) -> str:
        """Build the snake animation URL."""
        return f"https://raw.githubusercontent.com/{self.ctx['username']}/{self.ctx['username']}/output/github-snake-dark.svg"

    def build_stats_card_url(self) -> str:
        """Build the GitHub stats card URL."""
        return (
            "https://github-readme-stats.vercel.app/api"
            f"?username={self.ctx['username']}"
            f"&theme={self.stats_theme}&hide_border=true&bg_color=0d1117"
            "&show_icons=true&count_private=true&rank_icon=github"
        )

    def build_top_langs_url(self) -> str:
        """Build the top languages card URL."""
        return (
            "https://github-readme-stats.vercel.app/api/top-langs/"
            f"?username={self.ctx['username']}"
            f"&theme={self.stats_theme}&hide_border=true&bg_color=0d1117"
            "&layout=compact&langs_count=8"
        )

    def build_streak_url(self) -> str:
        """Build the streak stats URL."""
        return (
            "https://streak-stats.demolab.com/"
            f"?user={self.ctx['username']}"
            f"&theme={self.stats_theme}&hide_border=true&background=0d1117"
            f"&ring={self.hex}&fire={self.hex}&currStreakLabel={self.hex}"
        )

    def build_activity_graph_url(self) -> str:
        """Build the activity graph URL."""
        return (
            "https://github-readme-activity-graph.vercel.app/graph"
            f"?username={self.ctx['username']}"
            f"&bg_color=0d1117&color={self.hex}&line={self.hex}"
            f"&point=FFFFFF&area=true&area_color={self.hex}"
            "&hide_border=true&custom_title=Contribution+Activity"
        )

    def build_summary_cards_urls(self) -> list[str]:
        """Build the profile summary card URLs."""
        username = self.ctx["username"]
        return [
            f"https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username={username}&theme=radical",
            f"https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username={username}&theme=radical",
            f"https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username={username}&theme=radical",
        ]

    def build_trophies_url(self) -> str:
        """Build the GitHub profile trophy URL."""
        return (
            "https://github-profile-trophy.vercel.app/"
            f"?username={self.ctx['username']}&theme=radical"
            "&no-frame=true&no-bg=true&column=7&margin-w=15&margin-h=15"
        )

    def build_quotes_url(self) -> str:
        """Build the dev quote widget URL."""
        return "https://quotes-github-readme.vercel.app/api?type=horizontal&theme=radical"

    def build_skillicons_url(self, icons: list[str]) -> str:
        """Build the Skill Icons URL."""
        return f"https://skillicons.dev/icons?i={','.join(icons)}&theme=dark"

    def build_views_counter_url(self) -> str:
        """Build the profile views counter URL."""
        return (
            "https://komarev.com/ghpvc/"
            f"?username={self.ctx['username']}&label=Profile+Views"
            f"&color={self.hex}&style={self.badge_style}"
        )

    def build_footer_url(self) -> str:
        """Build the footer capsule URL."""
        return (
            "https://capsule-render.vercel.app/api"
            f"?type=waving&color=gradient&customColorList={self.gradient}"
            "&height=120&section=footer"
        )

    def build_language_badges(self) -> list[str]:
        """Build Markdown badge images for language proficiency rows."""
        badges: list[str] = []
        languages = self.ctx.get("languages", {})
        for language, data in sorted(languages.items(), key=lambda item: item[1]["percent"], reverse=True):
            logo = LANGUAGE_ICON_MAP.get(language, "")
            badge = self.build_badge(language, data["proficiency"], data["hex"], logo)
            badges.append(f"![{language}]({badge})")
        return badges

    def build_social_badges(self) -> list[str]:
        """Build clickable Markdown badges for detected social profiles."""
        badges: list[str] = []
        for platform, value in self.ctx.get("social_links", {}).items():
            logo, color = SOCIAL_LOGO_MAP.get(platform, ("github", self.hex))
            if color == "hex from config":
                color = self.hex
            target = value if platform == "email" else ensure_url_scheme(value)
            url = self.build_badge(platform.title(), platform.title(), color, logo)
            badges.append(f"[![{platform}]({url})]({target})")
        return badges

    def _typing_lines(self) -> list[str]:
        """Compute the three typing animation lines for the active mode."""
        if self.ctx["mode"] == "profile":
            bio = self.ctx.get("bio_parsed", {})
            role = ", ".join(bio.get("roles") or []) or "Open source builder"
            identity = ", ".join((bio.get("stack_keywords") or [])[:3]) or self.ctx["display_name"]
            cta = bio.get("fun_fact") or f"Explore {self.ctx['username']} on GitHub"
            return [role, identity, cta]

        project = self.ctx["project"]
        return [
            project.get("description") or project["name"],
            project.get("install_command") or "Install locally",
            "⭐ Star this repo",
        ]

    def _runtime_label(self, project: dict[str, Any]) -> str:
        """Infer a runtime badge label from project metadata."""
        package_manager = project.get("package_manager")
        if package_manager == "pip":
            return "Python"
        if package_manager == "npm":
            return "Node"
        if package_manager == "cargo":
            return "Rust"
        if package_manager == "go":
            return "Go"
        return "Runtime"
