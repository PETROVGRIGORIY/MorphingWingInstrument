from pathlib import Path
import math
import threading
from concurrent.futures import ThreadPoolExecutor

from tqdm.auto import tqdm

from ...facade.airfoil import Airfoil
from ..optimization_definition import (
    ObjectiveFunction,
    OptimizationSettings,
    MinCruiseDragOptSettings,
    MinCruiseDragResult,
    AirfoilDeformationStrategy
)
from ..objective_functions_evaluation.cruise_drag_evaluation import (
    evaluate_airfoil_drag
)
from ..optimization_report.exhaustive_search_report import (
    generate_exhaustive_report
)


def evaluate_af_sequence(
    airfoils,
    optimization_settings,
    deformate_strategy,
    position,
    desc,
    stop
) -> list[MinCruiseDragResult]:
    """Вычисляет характеристики набора профилей."""

    results = []

    for airfoil in tqdm(
        airfoils, desc=desc, unit="шт", position=position
    ):
        if stop.is_set():
            break

        try:
            result = evaluate_airfoil_drag(
                airfoil,
                optimization_settings,
                deformate_strategy
            )

        except Exception:
            result = MinCruiseDragResult(
                airfoil=airfoil,
                drag_X=None,
                cd_clmax_ratio=None,
                best_cl_max=None,
                best_deformation=None
            )

        results.append(result)

    return results


def launch_exhaustive_optimization(
    airfoil_sequence: list[Airfoil] | tuple[Airfoil, ...],
    objective_function: ObjectiveFunction,
    optimization_settings: OptimizationSettings,
    deformate_strategy: AirfoilDeformationStrategy | None = None,
    threads: int = 1,
    report_path: Path | None = None
) -> dict:
    """
    Поиск наилучшего профиля под заданную целевую функцию перебором.

    :param airfoil_sequence: Список или кортеж профилей Airfoil.
    :param objective_function: Целевая функция.
    :param optimization_settings: Настройки расчёта.
    :param deformate_strategy: Стратегия деформации профиля.
        Если None, расчёт выполняется без деформации.
    :param threads: Число потоков расчёта.
        Профили распределяются между потоками.
    :param report_path: Путь сохранения отчёта (.pdf или .md).
        Если None, отчёт не формируется.

    :return: Словарь с результатами оптимизации:
             1. result: Лучший найденный результат или None.
             2. results: Результаты расчёта всех профилей.
    :rtype: dict

    :raises ValueError: Если список профилей пуст, указано
        некорректное число потоков или формат отчёта.
    :raises TypeError: Если настройки не соответствуют целевой функции.
    :raises NotImplementedError: Если целевая функция не реализована.
    """

    # Проверка входных параметров
    if not airfoil_sequence:
        raise ValueError("airfoil_sequence пуст: нечего перебирать")

    if objective_function != ObjectiveFunction.MIN_CRUISE_DRAG:
        raise NotImplementedError(
            f"Целевая функция {objective_function} не реализована"
        )

    if not isinstance(optimization_settings, MinCruiseDragOptSettings):
        raise TypeError("Несовместимые настройки и целевая функция")

    if not isinstance(threads, int) or threads < 1:
        raise ValueError("threads должен быть целым числом не меньше 1")

    if report_path is not None:
        report_path = Path(report_path)

        if report_path.suffix.lower() not in (".pdf", ".md"):
            raise ValueError("Поддерживаются только форматы .pdf и .md")

    # Распределение профилей между потоками
    airfoils = list(airfoil_sequence)
    threads = min(threads, len(airfoils))

    parts = [airfoils[i::threads] for i in range(threads)]
    stop_event = threading.Event()

    def run_part(i: int):
        desc = "Перебор профилей" if threads == 1 else f"Поток {i + 1}"

        return evaluate_af_sequence(
            parts[i],
            optimization_settings,
            deformate_strategy,
            i,
            desc,
            stop_event
        )

    # Запуск параллельных вычислений
    print("Запуск оптимизации перебором.")

    with ThreadPoolExecutor(max_workers=threads) as pool:
        try:
            part_results = list(pool.map(run_part, range(threads)))

        except KeyboardInterrupt:
            stop_event.set()
            raise

    # Восстановление исходного порядка профилей
    results = [
        part_results[i % threads][i // threads]
        for i in range(len(airfoils))
    ]

    # Поиск лучшего профиля
    best_result = min(
        (
            result for result in results
            if result.drag_X is not None
            and math.isfinite(result.drag_X)
        ),
        key=lambda result: result.drag_X,
        default=None
    )

    # Сохранение отчёта
    if report_path is not None:
        generate_exhaustive_report(
            results=results,
            objective_function=objective_function,
            path=report_path
        )

    print("Оптимизация перебором завершена.")

    return {
        "result": best_result,
        "results": results
    }
