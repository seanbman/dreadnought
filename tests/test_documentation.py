from pathlib import Path


def test_all_markdown_has_index_and_provenance_process_appendix() -> None:
    root = Path(__file__).parents[1]
    markdown = [root / "README.md", root / "AGENTS.md", *sorted((root / "docs").glob("*.md"))]
    missing: list[str] = []
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        requirements = {
            "index": "## Index",
            "appendix": "## Appendix — Process flow",
            "mermaid": "```mermaid",
            "inception provenance": "inception:",
            "current provenance": "current:",
        }
        absent = [label for label, marker in requirements.items() if marker not in text]
        if absent:
            missing.append(f"{path.relative_to(root)}: {', '.join(absent)}")
    assert not missing, "documentation contract violations:\n" + "\n".join(missing)
