from pathlib import Path

from markdown_pdf import MarkdownPdf, Section


def save_report(markdown: str, path: Path) -> None:
    """Сохраняет отчёт в формате Markdown или PDF."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == ".md":
        path.write_text(markdown, encoding="utf-8")

    elif path.suffix.lower() == ".pdf":
        pdf = MarkdownPdf(toc_level=2)

        pdf.add_section(
            Section(markdown, root=str(path.parent.resolve()))
        )

        pdf.save(str(path))

    else:
        raise ValueError("Поддерживаются только форматы .md и .pdf")
