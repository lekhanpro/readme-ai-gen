"""Central configuration constants for readme-ai-gen."""

from __future__ import annotations

APP_NAME = "readme-ai-gen"
CLI_COMMAND = "readme-gen"
VERSION = "1.0.0"
DEFAULT_THEME = "purple"
DEFAULT_HEADER = "venom"
DEFAULT_ANIMATION = "twinkling"
DEFAULT_FONT = "JetBrains Mono"
DEFAULT_STATS_THEME = "radical"
DEFAULT_BADGE_STYLE = "for-the-badge"
DEFAULT_HEIGHT = 200
DEFAULT_OUTPUT_LENGTH = "200-350"
DEFAULT_TONE = "Professional, personal, developer-native."
DEFAULT_LLM = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OUTPUT = "./README.md"
REQUEST_TIMEOUT = 10.0
USER_AGENT = f"{APP_NAME}/{VERSION}"
GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = f"{GITHUB_API}/graphql"
RAW_GITHUB = "https://raw.githubusercontent.com"

THEMES = {
    "purple": {"hex": "A855F7", "rgb": "168,85,247", "gradient": "12,14,25,27"},
    "cyan": {"hex": "06B6D4", "rgb": "6,182,212", "gradient": "0,20,30,40"},
    "green": {"hex": "22C55E", "rgb": "34,197,94", "gradient": "0,15,10,20"},
    "orange": {"hex": "F97316", "rgb": "249,115,22", "gradient": "30,15,5,0"},
    "pink": {"hex": "EC4899", "rgb": "236,72,153", "gradient": "30,10,20,25"},
    "red": {"hex": "EF4444", "rgb": "239,68,68", "gradient": "30,10,5,0"},
    "gold": {"hex": "EAB308", "rgb": "234,179,8", "gradient": "30,20,10,5"},
    "blue": {"hex": "3B82F6", "rgb": "59,130,246", "gradient": "0,10,25,40"},
    "teal": {"hex": "14B8A6", "rgb": "20,184,166", "gradient": "0,25,20,15"},
    "slate": {"hex": "94A3B8", "rgb": "148,163,184", "gradient": "0,0,5,10"},
}

HEADER_TYPES = ["venom", "waving", "soft", "rect", "cylinder", "slice", "shark", "egg"]

ANIMATIONS = ["twinkling", "fadeIn", "scaleIn", "blink", "blinking"]

FONTS = [
    "JetBrains+Mono",
    "Fira+Code",
    "Orbitron",
    "Space+Mono",
    "Courier+Prime",
    "Roboto+Mono",
]

STATS_THEMES = [
    "radical",
    "tokyonight",
    "dracula",
    "midnight-purple",
    "synthwave",
    "github_dark",
]

BADGE_STYLES = ["for-the-badge", "flat-square", "flat", "plastic"]

CAPSULE_HEIGHTS = {"compact": 150, "normal": 200, "tall": 250, "hero": 300}

OUTPUT_LENGTHS = {
    "minimal": "100-150",
    "standard": "200-350",
    "detailed": "350-500",
    "exhaustive": "500+",
}

ALL_ICONS = [
    "py", "ts", "js", "java", "cpp", "c", "cs", "go", "rust", "ruby",
    "php", "swift", "kotlin", "dart", "r", "scala", "lua", "perl",
    "bash", "powershell",
    "react", "nextjs", "vue", "angular", "svelte", "nuxtjs", "gatsby", "astro",
    "nodejs", "express", "fastapi", "flask", "django", "spring",
    "laravel", "rails", "nestjs", "deno", "bun",
    "flutter", "androidstudio", "xcode",
    "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "githubactions", "circleci",
    "mysql", "postgres", "mongodb", "redis", "sqlite",
    "firebase", "supabase", "cassandra", "graphql",
    "aws", "gcp", "azure", "vercel", "netlify", "heroku", "cloudflare",
    "git", "github", "gitlab", "bitbucket",
    "linux", "ubuntu", "debian", "raspberrypi", "arch", "kali",
    "vscode", "idea", "vim", "neovim", "sublime",
    "figma", "postman", "insomnia",
    "html", "css", "sass", "tailwind", "bootstrap", "materialui",
    "tensorflow", "pytorch", "sklearn", "opencv",
    "anaconda", "jupyter",
    "kafka", "rabbitmq", "nginx", "apache",
]

LANGUAGE_COLORS = {
    "Python": "3776AB",
    "TypeScript": "3178C6",
    "JavaScript": "F7DF1E",
    "Java": "ED8B00",
    "Go": "00ADD8",
    "Rust": "DEA584",
    "C++": "00599C",
    "C": "A8B9CC",
    "C#": "239120",
    "Dart": "00B4AB",
    "Kotlin": "7F52FF",
    "Ruby": "CC342D",
    "PHP": "777BB4",
    "Swift": "F05138",
    "Shell": "4EAA25",
    "Bash": "4EAA25",
    "Scala": "DC322F",
    "R": "276DC3",
    "Lua": "2C2D72",
    "HTML": "E34F26",
    "CSS": "1572B6",
}

SOCIAL_LOGO_MAP = {
    "portfolio": ("safari", "hex from config"),
    "linkedin": ("linkedin", "0A66C2"),
    "twitter": ("x", "000000"),
    "youtube": ("youtube", "FF0000"),
    "instagram": ("instagram", "E4405F"),
    "discord": ("discord", "5865F2"),
    "pypi": ("pypi", "3775A9"),
    "npm": ("npm", "CB3837"),
    "orcid": ("orcid", "A6CE39"),
    "email": ("gmail", "EA4335"),
    "telegram": ("telegram", "26A5E4"),
}

PROFILE_SECTIONS_DEFAULT = [
    "header", "typing", "badges", "snake", "about",
    "ventures", "opensource", "tech", "stats",
    "contrib_graph", "trophies", "quote", "social", "footer",
]

PROJECT_SECTIONS_DEFAULT = [
    "header", "typing", "badges", "about", "features",
    "install", "usage", "tree", "tech", "contribute", "footer",
]

SECTION_ORDER = [
    "header", "typing", "badges", "snake", "about", "ventures", "opensource",
    "demo", "features", "install", "usage", "tree", "tech", "stats",
    "contrib_graph", "trophies", "quote", "social", "contribute", "footer",
]

LANGUAGE_ICON_MAP = {
    "Python": "py",
    "TypeScript": "ts",
    "JavaScript": "js",
    "Java": "java",
    "Go": "go",
    "Rust": "rust",
    "C++": "cpp",
    "C": "c",
    "C#": "cs",
    "Dart": "dart",
    "Kotlin": "kotlin",
    "Ruby": "ruby",
    "PHP": "php",
    "Swift": "swift",
    "Scala": "scala",
    "R": "r",
    "Lua": "lua",
    "Shell": "bash",
    "Bash": "bash",
    "HTML": "html",
    "CSS": "css",
}

TECH_KEYWORDS = [
    "python", "typescript", "javascript", "node", "react", "next", "vue", "angular",
    "fastapi", "flask", "django", "docker", "kubernetes", "terraform", "aws",
    "gcp", "azure", "pytorch", "tensorflow", "sklearn", "pandas", "postgres",
    "mongodb", "redis", "firebase", "linux", "graphql", "go", "rust", "java",
]

SECTION_LABELS = {
    "header": "header",
    "typing": "typing",
    "badges": "badges",
    "snake": "snake",
    "about": "about",
    "ventures": "ventures",
    "opensource": "opensource",
    "tech": "tech",
    "stats": "stats",
    "contrib_graph": "contrib_graph",
    "trophies": "trophies",
    "quote": "quote",
    "social": "social",
    "footer": "footer",
    "demo": "demo",
    "features": "features",
    "install": "install",
    "usage": "usage",
    "tree": "tree",
    "contribute": "contribute",
}
