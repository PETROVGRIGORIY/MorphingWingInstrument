import threading
from concurrent.futures import Future

from ..optimization_definition import (
    ObjectiveFunction, OptimizationSettings, OptimizationResult,
    AirfoilGenerationStrategy, AirfoilDeformationStrategy
)
from ..objective_functions_evaluation.cruise_drag_evaluation import (
    evaluate_airfoil_drag
)


def make_fitness_function(
        opt_settings: OptimizationSettings,
        objective_function: ObjectiveFunction,
        generation_strategy: AirfoilGenerationStrategy,
        deformate_strategy: AirfoilDeformationStrategy | None = None
    ):
    """Строит функцию приспособленности для PyGAD.
    generate_airfoil(*genes) -> Airfoil создаёт пользователь, opt_settings - условия задачи."""

    cache: dict[tuple, Future[tuple[float, OptimizationResult | None]]] = {}
    lock = threading.Lock()

    def fitness(ga_instance, solution, solution_idx) -> float:
        genes = tuple(
            g.item() if hasattr(g, "item") else g
            for g in solution
        )

        # Проверяем наличие расчёта в кэше
        with lock:
            future = cache.get(genes)
            is_owner = future is None

            if is_owner:
                future = cache[genes] = Future()

        # Только один поток рассчитывает данную хромосому
        if is_owner:
            value = 0.0
            result = None

            try:
                if objective_function == ObjectiveFunction.MIN_CRUISE_DRAG:
                    af = generation_strategy.generate_airfoil(*genes)

                    result = evaluate_airfoil_drag(
                        af, opt_settings, deformate_strategy
                    )

                    if result.drag_X is not None:
                        value = 1.0 / (result.drag_X + 1e-6)

            except Exception:
                value = 0.0
                result = None

            except BaseException as exc:
                future.set_exception(exc)
                raise

            future.set_result((value, result))

        # Остальные потоки ожидают завершения расчёта
        value, _ = future.result()
        return value

    fitness.cache = cache
    return fitness
