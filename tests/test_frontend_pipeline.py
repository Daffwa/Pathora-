from pathlib import Path

from tools.build_frontend_assets import (
    SourceLine,
    build_source_map,
    collect_css_lines,
    tree_shake_unused_functions,
)


def test_source_map_keeps_original_source_content(tmp_path, monkeypatch):
    source_path = tmp_path / "static" / "js" / "example.js"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("function hello() {\n    return true;\n}\n", encoding="utf-8")

    import tools.build_frontend_assets as builder

    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    source_map = build_source_map(
        "example.hash.min.js",
        [
            SourceLine("function hello() {", source_path, 1),
            SourceLine("return true;", source_path, 2),
        ],
    )

    assert source_map["version"] == 3
    assert source_map["file"] == "example.hash.min.js"
    assert source_map["sources"] == ["static/js/example.js"]
    assert "function hello()" in source_map["sourcesContent"][0]
    assert source_map["mappings"]


def test_tree_shaking_removes_unreferenced_function():
    source = Path("static/js/example.js")
    lines = [
        SourceLine("(function () {", source, 1),
        SourceLine("function unusedHelper() {", source, 2),
        SourceLine("return true;", source, 3),
        SourceLine("}", source, 4),
        SourceLine("function usedHelper() {", source, 5),
        SourceLine("return false;", source, 6),
        SourceLine("}", source, 7),
        SourceLine("usedHelper();", source, 8),
        SourceLine("})();", source, 9),
    ]

    shaken_lines, removed = tree_shake_unused_functions(lines)
    output = "\n".join(line.content for line in shaken_lines)

    assert removed == ["unusedHelper"]
    assert "unusedHelper" not in output
    assert "usedHelper" in output


def test_css_build_strips_utf8_bom_from_imported_selectors(tmp_path):
    css_dir = tmp_path / "static" / "css"
    partials_dir = css_dir / "partials"
    partials_dir.mkdir(parents=True)
    entry = css_dir / "style.css"
    partial = partials_dir / "layout.css"

    entry.write_text('@import url("./partials/layout.css");\n', encoding="utf-8")
    partial.write_text("\ufeff.site-header {\n    display: flex;\n}\n", encoding="utf-8")

    lines = collect_css_lines(entry)
    output = "\n".join(line.content for line in lines)

    assert "\ufeff" not in output
    assert ".site-header{" in output
