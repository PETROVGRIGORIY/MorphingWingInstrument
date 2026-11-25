import logging
from typing import Callable

from ...optimization_definition import (
    ObjectiveFunction, OptimizationSettings
)
from ...objective_functions_evaluation.cruise_drag_evaluation import evaluate_airfoil_drag

logger = logging.getLogger(__name__)


def make_fitness_function(
        generate_airfoil: Callable, 
        opt_settings: OptimizationSettings,
        objective_function: ObjectiveFunction
    ):
    """Строит функцию приспособленности для PyGAD.
    generate_airfoil(*genes) -> Airfoil создаёт пользователь, opt_settings - условия задачи."""
    cache: dict[tuple, float] = {}   # одинаковые хромосомы считаем один раз

    def fitness(ga_instance, solution, solution_idx) -> float:
        genes = tuple(g.item() if hasattr(g, "item") else g for g in solution)
        if genes in cache:
            return cache[genes]
        
        value = 0.0
        try:
            if objective_function == ObjectiveFunction.MIN_CRUISE_DRAG:
                result = evaluate_airfoil_drag(generate_airfoil(*genes), opt_settings)
                value = 0.0 if result.drag_X is None else 1.0 / (result.drag_X + 1e-6)
        except Exception:
            logger.exception("Ошибка расчёта для генов %s", genes)   # с трассировкой
            value = 0.0
        cache[genes] = value
        return value

    return fitness
