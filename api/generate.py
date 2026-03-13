"""Vercel serverless endpoint for web-based README generation."""

from __future__ import annotations

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler
from typing import Any

from dotenv import load_dotenv

from readme_ai_gen.config import (
    DEFAULT_ANIMATION,
    DEFAULT_BADGE_STYLE,
    DEFAULT_FONT,
    DEFAULT_HEADER,
    DEFAULT_HEIGHT,
    DEFAULT_LLM,
    DEFAULT_OUTPUT_LENGTH,
    DEFAULT_STATS_THEME,
    DEFAULT_TONE,
)
from readme_ai_gen.renderer import ReadmeRenderer
from readme_ai_gen.utils import (
    DependencyError,
    GitHubAPIError,
    LLMError,
    URLParseError,
    get_default_sections,
    order_sections,
    parse_csv_list,
    parse_github_url,
    resolve_theme,
)

load_dotenv()


def build_web_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Build the shared runtime config for web requests."""
    url = str(payload.get("url") or "").strip()
    if not url:
        raise URLParseError("GitHub URL is required.")

    _, repo, detected_mode = parse_github_url(url)
    requested_mode = str(payload.get("mode") or "auto").lower()
    if requested_mode == "auto":
        mode = detected_mode
    elif requested_mode == "project" and not repo:
        raise URLParseError("For project mode, use: https://github.com/username/repo-name")
    elif requested_mode == "profile" and repo:
        raise URLParseError("Could not parse GitHub URL. Expected: https://github.com/username")
    else:
        mode = requested_mode

    theme = resolve_theme(payload.get("color"))
    sections = payload.get("sections")
    if isinstance(sections, list):
        selected_sections = [str(section).strip() for section in sections if str(section).strip()]
    else:
        selected_sections = parse_csv_list(str(sections or ""))
    ordered_sections = order_sections({"header", *(selected_sections or get_default_sections(mode)), "footer"})

    icons = payload.get("icons") or []
    if isinstance(icons, str):
        icon_list = parse_csv_list(icons)
    else:
        icon_list = [str(icon).strip() for icon in icons if str(icon).strip()]

    provider = str(payload.get("llm") or os.getenv("DEFAULT_LLM", DEFAULT_LLM)).lower()
    if provider not in {"gemini", "openai"}:
        raise ValueError("Invalid provider. Use 'gemini' or 'openai'.")

    return {
        "mode": mode,
        "theme": theme["name"],
        "color": theme["hex"],
        "gradient": theme["gradient"],
        "header_type": str(payload.get("header_type") or DEFAULT_HEADER),
        "animation": str(payload.get("animation") or DEFAULT_ANIMATION),
        "font": str(payload.get("font") or DEFAULT_FONT).replace("+", " "),
        "stats_theme": str(payload.get("stats_theme") or DEFAULT_STATS_THEME),
        "badge_style": str(payload.get("badge_style") or DEFAULT_BADGE_STYLE),
        "height": int(payload.get("height") or DEFAULT_HEIGHT),
        "sections": ordered_sections,
        "icons": icon_list,
        "llm": provider,
        "gemini_model": os.getenv("GEMINI_MODEL") or None,
        "openai_model": os.getenv("OPENAI_MODEL") or None,
        "output_length": DEFAULT_OUTPUT_LENGTH,
        "tone": DEFAULT_TONE,
    }


class handler(BaseHTTPRequestHandler):
    """Serve README generation requests for the frontend."""

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Respond to CORS preflight requests."""
        self._write_json(204, {})

    def do_GET(self) -> None:  # noqa: N802
        """Expose a small health payload for the web client."""
        self._write_json(
            200,
            {
                "ok": True,
                "service": "readme-ai-gen",
                "providers": {
                    "gemini": bool(os.getenv("GEMINI_API_KEY")),
                    "openai": bool(os.getenv("OPENAI_API_KEY")),
                },
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        """Generate a README from the posted JSON payload."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw_body)
            config = build_web_config(payload)
            renderer = ReadmeRenderer()
            prepared, markdown = asyncio.run(
                renderer.render(
                    url=str(payload["url"]),
                    config=config,
                    provider=config["llm"],
                    github_token=os.getenv("GITHUB_TOKEN"),
                )
            )
            self._write_json(
                200,
                {
                    "ok": True,
                    "markdown": markdown,
                    "lineCount": len(markdown.splitlines()),
                    "mode": prepared.context["mode"],
                    "username": prepared.context["username"],
                    "repo": prepared.context.get("repo"),
                    "displayName": prepared.context["display_name"],
                    "summary": {
                        "repos": prepared.context["public_repos"],
                        "followers": prepared.context["followers"],
                        "stars": prepared.context["total_stars"],
                        "languages": list(prepared.context.get("languages", {}).keys())[:4],
                    },
                },
            )
        except json.JSONDecodeError:
            self._write_json(400, {"ok": False, "error": "Request body must be valid JSON."})
        except URLParseError as exc:
            self._write_json(400, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            self._write_json(400, {"ok": False, "error": str(exc)})
        except GitHubAPIError as exc:
            self._write_json(exc.status_code or 502, {"ok": False, "error": str(exc)})
        except (LLMError, DependencyError) as exc:
            self._write_json(500, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._write_json(500, {"ok": False, "error": f"Unexpected server error: {exc}"})

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        """Write a JSON response with permissive same-origin friendly headers."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)
