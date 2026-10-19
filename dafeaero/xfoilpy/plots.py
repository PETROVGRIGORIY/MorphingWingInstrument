import matplotlib.pyplot as plt
import numpy as np

import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ComparisonMode(StrEnum):
    COMBINED = "combined"
    """Все данные отображаются на одном графике (с легендой)."""

    SEPARATE = "separate"
    """Каждый набор данных отображается на отдельном графике."""


@dataclass
class PlotData:
    plot_name: str
    x: list | tuple | np.ndarray
    y: list | tuple | np.ndarray


def plots_to_comparison(
    data: list[PlotData],
    mode: ComparisonMode,
    x_axis_name: str,
    y_axis_name: str,
    plot_name: str = "",
    path: str | Path = ""
) -> None:
    """
    Строит графики сравнения данных
    data : Список кортежей с данными.
    mode : Режим компоновки: COMBINED (все на одном) или SEPARATE (на разных).
    """
    colors = ['blue', 'green', 'black', 'red', 'violet', 'cornflowerblue']

    if not data:
        return

    if mode == ComparisonMode.COMBINED:
        fig, ax = plt.subplots(figsize=(10, 6))

        for i, series in enumerate(data):
            color = colors[i % len(colors)]
            ax.plot(
                series.x,
                series.y,
                color=color,
                linewidth=2,
                label=series.plot_name
            )

        title = plot_name if plot_name else "Combined Comparison"
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel(x_axis_name)
        ax.set_ylabel(y_axis_name)
        ax.legend(loc='best')
        ax.minorticks_on()
        ax.grid(which='major', color = 'k',linestyle='--', linewidth = 1)
        ax.grid(which='minor', color = 'b', linestyle = ':')

    elif mode == ComparisonMode.SEPARATE:
        n_plots = len(data)

        cols = math.ceil(math.sqrt(n_plots))
        rows = math.ceil(n_plots / cols)

        fig, axes = plt.subplots(
            rows, cols, squeeze=False, figsize=(
                cols * 4.5, rows * 3.5))
        axes_flat = axes.flatten()

        for i, series in enumerate(data):
            ax = axes_flat[i]
            color = colors[i % len(colors)]

            ax.plot(series.x, series.y, color=color, linewidth=2)
            ax.set_title(series.plot_name, fontsize=12)
            ax.set_xlabel(x_axis_name)
            ax.set_ylabel(y_axis_name)
            ax.minorticks_on()
            ax.grid(which='major', color = 'k',linestyle='--', linewidth = 1)
            ax.grid(which='minor', color = 'b', linestyle = ':')

        # Скрываем пустые подграфики
        for j in range(n_plots, len(axes_flat)):
            axes_flat[j].set_visible(False)

        # Общий заголовок для сетки (если задан)
        if plot_name:
            fig.suptitle(plot_name, fontsize=16, fontweight='bold', y=1.02)

    fig.tight_layout()

    if path:
        save_path = Path(path)
        # Создаем директорию, если её не существует (защита от ошибок)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем с высоким DPI и обрезкой лишних полей
        fig.savefig(save_path, bbox_inches='tight', dpi=300)
        print(f"График успешно сохранен в: {save_path}")
    else:
        plt.show()

    # Закрываем фигуру, чтобы избежать утечек памяти при вызове в цикле
    plt.close(fig)
