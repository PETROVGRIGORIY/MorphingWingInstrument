from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import tempfile
import shutil

from markdown_pdf import MarkdownPdf, Section


class AirfoilReport(ABC):
    _objective_value: int | float
    _report_data: Any

    @abstractmethod
    def to_markdown(self, path: Path) -> None:
        """Генерирует Markdown файл для отчёта о конкретном профиле."""
        pass


class OptimizationReport():
    _airfoil_reports: list[AirfoilReport]

    def __init__(self, airfoil_reports: list[AirfoilReport] | None = None):
        if airfoil_reports is not None:
            self._airfoil_reports = airfoil_reports
        else:
            self._airfoil_reports = []

    def to_markdown(self, path: Path) -> None:
        """Собирает общий Markdown из отчетов отдельных профилей."""
        # Сортировка: от лучшего к худшему (по убы)
        self._airfoil_reports.sort(key=lambda r: r._objective_value)
        
        path.parent.mkdir(parents=True, exist_ok=True)
        img_dest_dir = path.parent / "report_img"
        img_dest_dir.mkdir(exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            final_md_content = "# Отчет по оптимизации\n\n"
            final_md_content += "| Профиль | Целевая функция |\n|---|---|\n"
            
            # 1. Сначала соберем краткую сводную таблицу
            for report in self._airfoil_reports:
                name = report._report_data.get("name", "Unknown")
                val = f"{report._objective_value:.4f}"
                final_md_content += f"| {name} | {val} |\n"
            
            final_md_content += "\n---\n\n"

            # 2. Теперь генерируем детальные отчеты во временной директории
            for i, report in enumerate(self._airfoil_reports):
                temp_md_path = temp_dir / f"airfoil_{i}.md"
                
                # Запускаем to_markdown дочернего класса. 
                # Он сохранит картинки в temp_dir (рядом с temp_md_path)
                report.to_markdown(temp_md_path)
                
                if temp_md_path.exists():
                    text = temp_md_path.read_text(encoding="utf-8")
                    final_md_content += text + "\n\n---\n\n"
            
            # 3. Сохраняем итоговый MD
            path.write_text(final_md_content, encoding="utf-8")
            
            # 4. Переносим картинки из временной папки в постоянную (рядом с MD)
            # Иначе после закрытия TemporaryDirectory они удалятся, и MD сломается
            for img_file in temp_dir.glob("*.png"):
                shutil.copy(img_file, img_dest_dir / img_file.name)

    def to_pdf(self, path: Path) -> None:
        """Генерирует PDF документ."""
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            temp_md_path = temp_dir / "temp_report.md"
            
            # 1. Генерируем MD прямо во временной директории (картинки тоже там)
            self.to_markdown(temp_md_path)
            
            # 2. Конвертируем в PDF, указывая root, чтобы PDF-движок нашел картинки
            pdf = MarkdownPdf(toc_level=2)
            pdf.add_section(
                Section(temp_md_path.read_text(encoding="utf-8"), root=str(temp_dir))
            )
            pdf.save(str(path))
