import logging
from pathlib import Path
import math
import threading
from concurrent.futures import ThreadPoolExecutor

from tqdm.auto import tqdm
import pandas as pd

from ...facade.airfoil import Airfoil
from ..optimization_definition import (
    ObjectiveFunction, OptimizationSettings, MinCruiseDragOptSettings
)
from ..objective_functions_evaluation.cruise_drag_evaluation import evaluate_airfoil_drag
from ..optimization_definition import MinCruiseDragResult
from ..optimization_report.report_base_classes import OptimizationReport
from ..optimization_report.cruise_drag_optimization_report import MinCruiseDragAirfoilReport

logger = logging.getLogger(__name__)


def evaluate_af_sequence(airfoils, optimization_settings, position, desc, stop):
    """Перебором вычисляет характеристики набора профилей под заданную целевую функцию"""
    reports = []
    for airfoil in tqdm(airfoils, desc=desc, unit="шт", position=position):
        if stop.is_set():     # прерывание пользователем
            break
        try:
            result = evaluate_airfoil_drag(airfoil, optimization_settings)
        except Exception:
            result = MinCruiseDragResult(
                airfoil=airfoil,
                drag_X=float("inf"),
                best_flap_angle=None,
                best_hinge_x=None,
                best_cl_max=None,
                scan_df=pd.DataFrame(),
            )
        reports.append(MinCruiseDragAirfoilReport(result))
    return reports


def launch_exhaustive_optimization(
    airfoil_sequence: list[Airfoil] | tuple[Airfoil, ...],
    objective_function: ObjectiveFunction,
    optimization_settings: OptimizationSettings,
    threads: int = 1,
    report_path: Path | None = None
) -> dict:
    """
    Поиск наилучшего профиля под заданную целевую функцию перебором.

    :param airfoil_sequence: Список или кортеж профилей Airfoil.
    :param objective_function: Целевая функция.
    :param optimization_settings: Настройки расчёта.
    :param threads: Число потоков расчёта (профили делятся между ними поровну).
        Не больше числа ядер процессора минус один.
    :param report_path:
        Если не None, сохраняет PDF-отчёт по этому пути.
    :return:
        Словарь с результатами перебора и объектом OptimizationReport.
    """
    if not airfoil_sequence:
        raise ValueError("airfoil_sequence пуст: нечего перебирать")
    if objective_function != ObjectiveFunction.MIN_CRUISE_DRAG:
        raise NotImplementedError
    if not isinstance(optimization_settings, MinCruiseDragOptSettings):
        raise TypeError("Несовместимые настройки и целевая функция")
    if not isinstance(threads, int) or threads < 1:
        raise ValueError("threads должен быть целым числом не меньше 1")
    
    reports = []
    airfoils = list(airfoil_sequence)
    threads = min(threads, len(airfoils))
    # Профили раздаются потокам вперемешку: так «трудные» профили не в одной нити
    parts = [airfoils[i::threads] for i in range(threads)]
    stop_event = threading.Event()

    def run_part(i: int):
        desc = "Перебор профилей" if threads == 1 else f"Поток {i + 1}"
        return evaluate_af_sequence(parts[i], optimization_settings, i, desc, stop_event)

    print("Запуск оптимизации перебором.")
    with ThreadPoolExecutor(max_workers=threads) as pool:
        try:
            part_reports = list(pool.map(run_part, range(threads)))
        # Остановка ячейки: потоки закончат текущий профиль и выйдут
        except KeyboardInterrupt:
            stop_event.set()
            raise

    reports = [None] * len(airfoils)     # Возвращаем исходный порядок профилей
    for i, part in enumerate(part_reports):
        reports[i::threads] = part
    report = OptimizationReport(reports)

    # Сохранение pdf файла
    if report_path is not None:
        path = Path(report_path)
        if path.is_dir():
            path = path / "report.pdf"
        elif path.suffix.lower() != ".pdf":
            path = path.with_suffix(".pdf")
        path.parent.mkdir(parents=True, exist_ok=True)
        report.to_pdf(path)

    best_af_report = next(
        (r for r in sorted(reports, key=lambda x: x._objective_value)
        if math.isfinite(r._objective_value)),
        None,
    )
    print("Оптимизация перебором завершена.")

    if best_af_report is None:
        return {"airfoil": None, "drag_X": None, "report": report}

    return {
        "airfoil": best_af_report._report_data.airfoil,
        "drag_X": best_af_report._objective_value,
        "report": report,
    }
