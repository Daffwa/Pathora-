import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATE_DIR = PROJECT_ROOT / "templates"

JS_FORBIDDEN_PATTERNS = {
    r"\bdebugger\b": "Remove debugger statements before shipping.",
    r"\beval\s*\(": "Avoid eval; it makes code harder to secure and debug.",
    r"\.innerHTML\s*=": "Prefer textContent or DOM nodes over innerHTML assignment.",
    r"\.insertAdjacentHTML\s*\(": "Prefer DOM node construction over insertAdjacentHTML.",
    r"\bconsole\.(log|debug|trace)\s*\(": "Remove debug console calls before shipping.",
}
INLINE_HANDLER_RE = re.compile(r"\s(onclick|onchange|onsubmit|oninput|onload)=")
SCRIPT_OPEN_RE = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)


def relative(path):
    return path.relative_to(PROJECT_ROOT).as_posix()


def add_error(errors, path, line_number, message):
    errors.append(f"{relative(path)}:{line_number}: {message}")


def lint_js_file(path, errors):
    text = path.read_text(encoding="utf-8")
    if not text.lstrip().startswith("(function"):
        add_error(errors, path, 1, "Wrap page scripts in an IIFE to avoid globals.")

    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern, message in JS_FORBIDDEN_PATTERNS.items():
            if re.search(pattern, line):
                add_error(errors, path, line_number, message)


def lint_css_file(path, errors):
    text = path.read_text(encoding="utf-8")
    brace_balance = 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        brace_balance += line.count("{") - line.count("}")
        if "\t" in line:
            add_error(errors, path, line_number, "Use spaces instead of tabs in CSS.")
        if line.rstrip() != line:
            add_error(errors, path, line_number, "Remove trailing whitespace.")

    if brace_balance != 0:
        add_error(errors, path, 1, "CSS braces are not balanced.")


def lint_template_file(path, errors):
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        script_match = SCRIPT_OPEN_RE.search(line)
        if script_match and "src=" not in script_match.group(1):
            add_error(errors, path, line_number, "Use external JS files instead of inline scripts.")
        if INLINE_HANDLER_RE.search(line):
            add_error(errors, path, line_number, "Use data attributes and external JS instead of inline handlers.")


def main():
    errors = []
    for path in sorted((STATIC_DIR / "js").glob("*.js")):
        lint_js_file(path, errors)
    for path in sorted((STATIC_DIR / "css").glob("*.css")):
        if path.name.endswith(".backup.css"):
            continue
        lint_css_file(path, errors)
    for path in sorted((STATIC_DIR / "css" / "partials").glob("*.css")):
        lint_css_file(path, errors)
    for path in sorted(TEMPLATE_DIR.rglob("*.html")):
        lint_template_file(path, errors)

    if errors:
        print("Frontend lint failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Frontend lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
