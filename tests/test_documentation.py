import re
from pathlib import Path


ARCHITECTURE_DOCS = {
    "docs/ARCHITECTURE.md",
    "docs/ARCHITECTURE_CHARTER.md",
    "docs/PROJECT_ARM_LEDGER.md",
    "docs/PROTOCOL_LEDGER.md",
    "docs/SARCOPHAGUS_LEDGER.md",
}


def _markdown(root: Path) -> list[Path]:
    return [root / "README.md", root / "AGENTS.md", *sorted((root / "docs").glob("*.md"))]


def test_all_markdown_has_index_and_provenance_process_appendix() -> None:
    root = Path(__file__).parents[1]
    missing: list[str] = []
    for path in _markdown(root):
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


def test_architecture_documents_have_code_linked_architecture_diagrams() -> None:
    root = Path(__file__).parents[1]
    violations: list[str] = []
    for relative in sorted(ARCHITECTURE_DOCS):
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if "## Architecture diagram" not in text:
            violations.append(f"{relative}: missing Architecture diagram section")
            continue
        if "code: src/" not in text and "code: .github/" not in text:
            violations.append(f"{relative}: architecture diagram has no repository code path")
        if text.count("```mermaid") < 2:
            violations.append(f"{relative}: requires separate architecture and process Mermaid diagrams")
        if relative != "docs/ARCHITECTURE.md" and "ARCHITECTURE.md" not in text:
            violations.append(f"{relative}: missing link to root architecture")
    assert not violations, "architecture documentation violations:\n" + "\n".join(violations)


def test_architecture_process_nodes_reference_code_and_commits() -> None:
    root = Path(__file__).parents[1]
    violations: list[str] = []
    node_pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\[\"(.*?)\"\]", re.DOTALL)
    for relative in sorted(ARCHITECTURE_DOCS):
        text = (root / relative).read_text(encoding="utf-8")
        appendix = text.split("## Appendix — Process flow", 1)[1]
        match = re.search(r"```mermaid\n(.*?)\n```", appendix, re.DOTALL)
        if not match:
            violations.append(f"{relative}: process Mermaid block missing")
            continue
        nodes = node_pattern.findall(match.group(1))
        if not nodes:
            violations.append(f"{relative}: process diagram contains no parsable nodes")
            continue
        for node in nodes:
            for marker in ("code:", "inception:", "current:"):
                if marker not in node:
                    violations.append(f"{relative}: process node missing {marker} {node[:50]!r}")
    assert not violations, "process-node provenance violations:\n" + "\n".join(violations)
