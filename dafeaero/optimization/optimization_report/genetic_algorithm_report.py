from pathlib import Path

from ..optimization_definition import (
    OptimizationResult,
    ObjectiveFunction
)
from .objective_renderers import (
    get_objective_value,
    format_cd_clmax_ratio,
    render_result
)
from .report_utils import save_report


def generate_ga_report(
    best_result: OptimizationResult | None,
    generation_results: list[OptimizationResult | None],
    objective_function: ObjectiveFunction,
    path: Path
) -> None:
    """Формирует отчёт о генетической оптимизации."""

    path = Path(path)
    assets_dir = path.parent / f"{path.stem}_img"

    md = "# Отчёт по генетической оптимизации\n\n"
    md += f"**Целевая функция:** {objective_function.value}\n\n"

    # Глобальный победитель
    md += "## Лучший профиль\n\n"

    if get_objective_value(best_result, objective_function) is not None:
        md += render_result(
            best_result,
            objective_function,
            assets_dir
        )
    else:
        md += "Оптимальный профиль не найден.\n\n"

    # Победители поколений
    md += "## Результаты поколений\n\n"

    md += "| Поколение | Лучший профиль | Сопротивление, Н | Cd / Cl_max |\n"
    md += "|---:|---|---:|---:|\n"

    for number, result in enumerate(generation_results):

        value = get_objective_value(result, objective_function)

        name = result.airfoil.name if result is not None else "—"
        drag_text = f"{value:.6g}" if value is not None else "Ошибка"
        ratio_text = format_cd_clmax_ratio(result)

        md += (
            f"| {number} "
            f"| {name} "
            f"| {drag_text} "
            f"| {ratio_text} |\n"
        )

    save_report(md, path)
