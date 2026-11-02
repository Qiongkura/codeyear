"""File path -> programming language mapping and noise filtering."""

from __future__ import annotations

from pathlib import Path

# Extensions we count as "code" in the language chart.
EXT_LANG: dict[str, str] = {
    # Python
    ".py": "Python", ".pyw": "Python", ".pyi": "Python",
    # Web
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS", ".less": "LESS",
    # JVM / .NET
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".groovy": "Groovy",
    ".cs": "C#", ".fs": "F#", ".vb": "Visual Basic",
    # Native
    ".c": "C", ".h": "C/C++", ".cc": "C++", ".cpp": "C++", ".cxx": "C++",
    ".hpp": "C++", ".hh": "C++", ".hxx": "C++", ".m": "Objective-C",
    ".mm": "Objective-C++", ".swift": "Swift", ".go": "Go", ".rs": "Rust",
    ".zig": "Zig", ".nim": "Nim", ".d": "D", ".v": "V",
    # Scripts
    ".rb": "Ruby", ".php": "PHP", ".lua": "Lua", ".pl": "Perl", ".r": "R",
    ".jl": "Julia", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
    ".erl": "Erlang", ".hs": "Haskell", ".scala": "Scala", ".clj": "Clojure",
    ".rkt": "Racket", ".lisp": "Lisp", ".el": "Emacs Lisp",
    # Shell
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
    ".ps1": "PowerShell", ".psm1": "PowerShell", ".bat": "Batch", ".cmd": "Batch",
    # Data / query
    ".sql": "SQL", ".graphql": "GraphQL", ".gql": "GraphQL", ".proto": "Protobuf",
    # Docs / config
    ".md": "Markdown", ".mdx": "MDX", ".rst": "reStructuredText", ".tex": "TeX",
    ".json": "JSON", ".jsonc": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".ini": "INI", ".cfg": "Config", ".conf": "Config",
    # Notebooks / shaders / embedded
    ".ipynb": "Jupyter", ".glsl": "Shader", ".hlsl": "Shader", ".wgsl": "Shader",
    ".metal": "Shader", ".ino": "Arduino", ".pde": "Processing",
    ".asm": "Assembly", ".s": "Assembly", ".sol": "Solidity",
}

NAME_LANG: dict[str, str] = {
    "dockerfile": "Docker",
    "makefile": "Makefile",
    "cmakelists.txt": "CMake",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
    "procfile": "Config",
    "justfile": "Makefile",
    ".gitignore": "Config",
    ".gitattributes": "Config",
    ".editorconfig": "Config",
}

# Binary / generated / data files that must never count as source lines.
SKIP_EXTS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff",
    ".psd", ".ai", ".eps", ".pdf", ".svg",
    ".zip", ".gz", ".tgz", ".bz2", ".xz", ".tar", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".a", ".lib", ".o", ".obj", ".class",
    ".jar", ".war", ".apk", ".ipa", ".wasm", ".pyc", ".pyo", ".pyd",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".wav", ".flac", ".ogg",
    ".bin", ".dat", ".db", ".sqlite", ".sqlite3",
    ".pt", ".pth", ".onnx", ".ckpt", ".safetensors", ".npy", ".npz", ".pkl",
    ".parquet", ".feather", ".arrow",
    ".csv", ".tsv", ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".ppt",
}

SKIP_NAMES: set[str] = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb",
    "cargo.lock", "poetry.lock", "pipfile.lock", "composer.lock",
    "go.sum", "gemfile.lock", "flake.lock", "npm-shrinkwrap.json",
    ".ds_store", "thumbs.db", "desktop.ini",
}

SKIP_PARTS: set[str] = {
    "node_modules", "bower_components", "dist", "build", "out", "output",
    "target", "vendor", "third_party", "third-party", "coverage", "htmlcov",
    ".next", ".nuxt", ".svelte-kit", ".parcel-cache", ".turbo",
    "__pycache__", ".venv", "venv", "env", "site-packages",
    "pods", "deriveddata", ".gradle", ".m2", "obj", "bin",
    "codeyear-output",
}

# Languages that are technically text but not interesting for "most edited files".
NON_CODE_LANGS: set[str] = {
    "Markdown", "MDX", "reStructuredText", "TeX", "JSON", "YAML", "TOML",
    "INI", "Config", "Jupyter",
}


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def is_skipped(path: str) -> bool:
    """Return True for binary, generated, vendored or lock files."""
    p = normalize_path(path).strip()
    if not p:
        return True
    parts = [x.lower() for x in p.split("/") if x]
    if not parts:
        return True
    name = parts[-1]
    if name in SKIP_NAMES:
        return True
    if name.endswith((".min.js", ".min.css", ".map", ".lock", ".sum")):
        return True
    if any(part in SKIP_PARTS for part in parts[:-1]):
        return True
    suffix = Path(name).suffix.lower()
    if suffix in SKIP_EXTS:
        return True
    return False


def language_for(path: str) -> str | None:
    """Map a repo-relative path to a language, or None if it should be ignored."""
    if is_skipped(path):
        return None
    p = normalize_path(path)
    name = p.rsplit("/", 1)[-1].lower()
    if name in NAME_LANG:
        return NAME_LANG[name]
    suffix = Path(name).suffix.lower()
    return EXT_LANG.get(suffix)


def is_code_language(lang: str | None) -> bool:
    return bool(lang) and lang not in NON_CODE_LANGS
