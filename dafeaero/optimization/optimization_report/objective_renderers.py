import math
from pathlib import Path

import matplotlib.pyplot as plt

from ..optimization_definition import (
    ObjectiveFunction,
    OptimizationResult,
    MinCruiseDragResult
)


def get_objective_value(
    result: OptimizationResult | None,
    objective_function: ObjectiveFunction
) -> float | None:
    """Возвращает значение целевой функции."""

    if objective_function != ObjectiveFunction.MIN_CRUISE_DRAG:
        raise NotImplementedError

    if result is None:
        return None

    if not isinstance(result, MinCruiseDragResult):
        raise TypeError("Несоответствие результата и целевой функции")

    value = result.drag_X

    if value is None or not math.isfinite(value):
        return None

    return value


def format_cd_clmax_ratio(
    result: OptimizationResult | None
) -> str:
    """Возвращает отформатированное отношение Cd / Cl_max."""

    if result is None:
        return "—"

    if not isinstance(result, MinCruiseDragResult):
        raise TypeError("Неподдерживаемый тип результата")

    value = result.cd_clmax_ratio

    if value is None or not math.isfinite(value):
        return "—"

    return f"{value:.6g}"


def render_result(
    result: OptimizationResult,
    objective_function: ObjectiveFunction,
    assets_dir: Path
) -> str:
    """Формирует подробное описание аэродинамического результата."""

    if objective_function != ObjectiveFunction.MIN_CRUISE_DRAG:
        raise NotImplementedError

    if not isinstance(result, MinCruiseDragResult):
        raise TypeError("Несоответствие результата и целевой функции")

    af = result.airfoil
    md = f"### {af.name}\n\n"

    drag = get_objective_value(result, objective_function)
    drag_text = f"{drag:.6g} Н" if drag is not None else "Ошибка"

    # Аэродинамические характеристики
    md += f"**Сопротивление:** {drag_text}\n\n"
    md += f"**Cd / Cl_max:** {format_cd_clmax_ratio(result)}\n\n"
    md += f"**Cl_max:** {result.best_cl_max}\n\n"
    md += f"**Параметры деформации:** {result.best_deformation}\n\n"

    # Геометрия профиля
    md += f"**Относительная толщина:** {af.thickness:.4f}\n\n"
    md += f"**Относительная кривизна:** {af.camber:.4f}\n\n"

    # График профиля
    assets_dir.mkdir(parents=True, exist_ok=True)

    img_name = "best_airfoil.png"

    try:
        ax = af.plot(show=False)

        try:
            ax.figure.savefig(
                assets_dir / img_name,
                dpi=150,
                bbox_inches="tight"
            )
        finally:
            plt.close(ax.figure)

        md += f"![{af.name}]({assets_dir.name}/{img_name})\n\n"

    except Exception:
        md += "Не удалось построить контур профиля.\n\n"

    return md
