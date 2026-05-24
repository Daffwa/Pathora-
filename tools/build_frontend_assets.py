import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
DIST_DIR = STATIC_DIR / "dist"
CSS_ENTRY = STATIC_DIR / "css" / "style.css"
JS_DIR = STATIC_DIR / "js"

CSS_IMPORT_RE = re.compile(r'^\s*@import\s+url\(["\']?([^"\')]+)["\']?\);\s*$')
JS_FUNCTION_RE = re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(")
SOURCE_MAP_VERSION = 3
BASE64_DIGITS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
UTF8_BOM = "\ufeff"


@dataclass(frozen=True)
class SourceLine:
    content: str
    source: Path
    line: int


def read_text(path):
    return path.read_text(encoding="utf-8").lstrip(UTF8_BOM)


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def content_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def compact_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()


def strip_css_comments_preserve_lines(content):
    return re.sub(
        r"/\*.*?\*/",
        lambda match: "\n" * match.group(0).count("\n"),
        content,
        flags=re.DOTALL,
    )


def compact_css_line(line):
    line = line.replace(UTF8_BOM, "")
    line = compact_whitespace(line)
    line = re.sub(r"\s*([{}:;,>+~])\s*", r"\1", line)
    return line.replace(";}", "}")


def collect_css_lines(path, seen=None):
    seen = seen or set()
    resolved_path = path.resolve()
    if resolved_path in seen:
        raise RuntimeError(f"Circular CSS import detected: {path}")

    seen.add(resolved_path)
    lines = []
    content = strip_css_comments_preserve_lines(read_text(path))
    for index, raw_line in enumerate(content.splitlines(), start=1):
        match = CSS_IMPORT_RE.match(raw_line)
        if match:
            import_target = match.group(1).split("?", 1)[0]
            imported_path = (path.parent / import_target).resolve()
            lines.extend(collect_css_lines(imported_path, seen.copy()))
            continue

        compacted = compact_css_line(raw_line)
        if compacted:
            lines.append(SourceLine(compacted, resolved_path, index))

    return lines


def brace_delta(line):
    return line.count("{") - line.count("}")


def find_function_blocks(lines):
    blocks = []
    index = 0
    while index < len(lines):
        match = JS_FUNCTION_RE.search(lines[index].content)
        if not match:
            index += 1
            continue

        depth = 0
        end = index
        while end < len(lines):
            depth += brace_delta(lines[end].content)
            if end > index and depth <= 0:
                break
            end += 1

        blocks.append(
            {
                "name": match.group(1),
                "start": index,
                "end": min(end, len(lines) - 1),
            }
        )
        index = min(end + 1, len(lines))

    return blocks


def tree_shake_unused_functions(lines):
    removed = []
    current_lines = lines

    while True:
        blocks = find_function_blocks(current_lines)
        remove_ranges = []

        for block in blocks:
            name = block["name"]
            outside = [
                line.content
                for line_index, line in enumerate(current_lines)
                if not (block["start"] <= line_index <= block["end"])
            ]
            outside_text = "\n".join(outside)
            if not re.search(rf"\b{re.escape(name)}\b", outside_text):
                remove_ranges.append((block["start"], block["end"], name))

        if not remove_ranges:
            return current_lines, removed

        next_lines = []
        cursor = 0
        for start, end, name in remove_ranges:
            next_lines.extend(current_lines[cursor:start])
            removed.append(name)
            cursor = end + 1
        next_lines.extend(current_lines[cursor:])
        current_lines = next_lines


def compact_js_line(line):
    stripped = line.strip()
    if not stripped or stripped.startswith("//"):
        return ""
    if stripped in {"debugger;", "debugger"}:
        return ""
    return stripped


def collect_js_lines(path):
    lines = []
    for index, raw_line in enumerate(read_text(path).splitlines(), start=1):
        compacted = compact_js_line(raw_line)
        if compacted:
            lines.append(SourceLine(compacted, path.resolve(), index))
    return tree_shake_unused_functions(lines)


def to_vlq_signed(value):
    if value < 0:
        return ((-value) << 1) + 1
    return value << 1


def encode_vlq(value):
    encoded = ""
    value = to_vlq_signed(value)

    while True:
        digit = value & 31
        value >>= 5
        if value:
            digit |= 32
        encoded += BASE64_DIGITS[digit]
        if not value:
            return encoded


def build_source_map(output_name, source_lines):
    sources = []
    source_indexes = {}
    for line in source_lines:
        source_name = line.source.relative_to(PROJECT_ROOT).as_posix()
        if source_name not in source_indexes:
            source_indexes[source_name] = len(sources)
            sources.append(source_name)

    previous_source = 0
    previous_original_line = 0
    previous_original_column = 0
    mapping_lines = []
    for line in source_lines:
        source_index = source_indexes[line.source.relative_to(PROJECT_ROOT).as_posix()]
        original_line = line.line - 1
        segment = (
            encode_vlq(0)
            + encode_vlq(source_index - previous_source)
            + encode_vlq(original_line - previous_original_line)
            + encode_vlq(0 - previous_original_column)
        )
        mapping_lines.append(segment)
        previous_source = source_index
        previous_original_line = original_line
        previous_original_column = 0

    return {
        "version": SOURCE_MAP_VERSION,
        "file": output_name,
        "sources": sources,
        "sourcesContent": [read_text(PROJECT_ROOT / source) for source in sources],
        "names": [],
        "mappings": ";".join(mapping_lines),
    }


def write_asset_with_map(asset_path, source_lines, source_map):
    map_path = asset_path.with_name(f"{asset_path.name}.map")
    output_name = asset_path.name
    if asset_path.suffix == ".css":
        content = "\n".join(line.content for line in source_lines)
        content += f"\n/*# sourceMappingURL={map_path.name} */\n"
    else:
        content = "\n".join(line.content for line in source_lines)
        content += f"\n//# sourceMappingURL={map_path.name}\n"

    write_text(asset_path, content)
    write_text(map_path, json.dumps(source_map, separators=(",", ":")))


def build_css(manifest):
    source_lines = collect_css_lines(CSS_ENTRY)
    content_for_hash = "\n".join(line.content for line in source_lines)
    digest = content_hash(content_for_hash)
    dist_path = DIST_DIR / "css" / f"style.{digest}.min.css"
    source_map = build_source_map(dist_path.name, source_lines)

    write_asset_with_map(dist_path, source_lines, source_map)
    manifest["assets"]["css/style.css"] = dist_path.relative_to(STATIC_DIR).as_posix()
    manifest["source_maps"]["css/style.css"] = (
        dist_path.with_name(f"{dist_path.name}.map").relative_to(STATIC_DIR).as_posix()
    )


def build_js(manifest):
    for source_path in sorted(JS_DIR.glob("*.js")):
        source_lines, removed_functions = collect_js_lines(source_path)
        content_for_hash = "\n".join(line.content for line in source_lines)
        digest = content_hash(content_for_hash)
        dist_path = DIST_DIR / "js" / f"{source_path.stem}.{digest}.min.js"
        source_map = build_source_map(dist_path.name, source_lines)

        write_asset_with_map(dist_path, source_lines, source_map)
        manifest_key = f"js/{source_path.name}"
        manifest["assets"][manifest_key] = dist_path.relative_to(STATIC_DIR).as_posix()
        manifest["source_maps"][manifest_key] = (
            dist_path.with_name(f"{dist_path.name}.map").relative_to(STATIC_DIR).as_posix()
        )
        manifest["tree_shaking"][manifest_key] = {
            "strategy": "conservative-unused-function-pruning",
            "removed_unused_functions": removed_functions,
        }


def build_assets():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assets": {},
        "source_maps": {},
        "tree_shaking": {},
    }
    build_css(manifest)
    build_js(manifest)
    write_text(DIST_DIR / "asset-manifest.json", json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    built_manifest = build_assets()
    print(
        "Built "
        f"{len(built_manifest['assets'])} frontend assets "
        f"and {len(built_manifest['source_maps'])} source maps in {DIST_DIR}"
    )
