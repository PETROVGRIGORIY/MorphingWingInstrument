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


def generate_exhaustive_report(
    results: list[OptimizationResult],
    objective_function: ObjectiveFunction,
    path: Path
) -> None:
    """Формирует отчёт об оптимизации полным перебором."""

    path = Path(path)
    assets_dir = path.parent / f"{path.stem}_img"

    # Сортировка результатов
    ranked_results = [
        (result, get_objective_value(result, objective_function))
        for result in results
    ]

    ranked_results.sort(
        key=lambda item: (
            item[1] if item[1] is not None else float("inf")
        )
    )

    md = "# Отчёт по оптимизации перебором\n\n"
    md += f"**Целевая функция:** {objective_function.value}\n\n"

    # Победитель
    md += "## Лучший профиль\n\n"

    if ranked_results and ranked_results[0][1] is not None:
        best_result = ranked_results[0][0]

        md += render_result(
            best_result,
            objective_function,
            assets_dir
        )
    else:
        md += "Оптимальный профиль не найден.\n\n"

    # Таблица всех профилей
    md += "## Результаты перебора\n\n"

    md += "| № | Профиль | Сопротивление, Н | Cd / Cl_max |\n"
    md += "|---:|---|---:|---:|\n"

    for i, (result, value) in enumerate(ranked_results, start=1):

        drag_text = f"{value:.6g}" if value is not None else "Ошибка"
        ratio_text = format_cd_clmax_ratio(result)

        md += (
            f"| {i} "
            f"| {result.airfoil.name} "
            f"| {drag_text} "
            f"| {ratio_text} |\n"
        )

    save_report(md, path)
