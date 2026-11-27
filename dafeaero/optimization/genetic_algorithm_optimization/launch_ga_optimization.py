import yaml
import pygad

from pathlib import Path

from ..optimization_definition import (
    ObjectiveFunction,
    OptimizationSettings, MinCruiseDragOptSettings,
    AirfoilGenerationStrategy, AirfoilDeformationStrategy
)
from ..optimization_report.genetic_algorithm_report import generate_ga_report
from .fitness_evaluator import make_fitness_function
from ...service.parametr_sequence import ParameterSequence


def _load_settings(path: Path) -> dict:
    """Читает YAML-файл с настройками."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_gene_space(
    gene_space: tuple[list|tuple|ParameterSequence, ...]) -> tuple[list, list[type]]:
    """
    Преобразует пользовательское описание пространства генов в формат, 
    понятный для PyGAD.
    
    Функция анализирует каждый элемент и определяет:
    - Является ли ген целочисленным или дробным.
    - Является ли это явным перечислением значений или диапазоном.
    
    Пример использования:
        gene_space = (
            (0, 7),                              # целый диапазон (0, 1, ..., 7)
            (1, 8),                              # целый диапазон (1, 2, ..., 8)
            ParameterSequence(6, 15),            # явное перечисление (6, 7, ..., 15)
            (0.6, 0.8)                           # дробный диапазон (float)
        )
        pygad_space, gene_types = parse_gene_space(gene_space)

    :param gene_space: Кортеж, содержащий описания генов. Каждый элемент может быть:
        - list: явный список допустимых значений.
        - tuple из 2 элементов: диапазон [min, max]. Если оба числа 
            целые, создается range (включительно). Если хотя бы одно 
            дробное — создается непрерывный float-диапазон.
        - ParameterSequence: объект, содержащий последовательность значений.
    :type gene_space: tuple[list | tuple | ParameterSequence]
    
    :return: Кортеж из двух элементов:
             1. pygad_space (list): Список пространств генов для передачи в PyGAD.
             2. gene_types (list[type]): Список типов данных (int или float) для каждого гена.
    :rtype: tuple[list, list[type]]
    
    :raises TypeError: Если переданный объект не является списком, кортежем 
                       из 2 элементов или ParameterSequence.
    """
    pygad_space, gene_types = [], []
    for spec in gene_space:
        if isinstance(spec, ParameterSequence):
            values = spec.values()
        elif isinstance(spec, list):
            values = spec
        elif isinstance(spec, tuple) and len(spec) == 2:
            low, high = spec
            if isinstance(low, int) and isinstance(high, int):
                values = list(range(low, high + 1))
            else:                                       # дробный диапазон
                pygad_space.append({'low': low, 'high': high})
                gene_types.append(float)
                continue
        else:
            raise TypeError(f"Не удалось разобрать описание гена: {spec!r}")
        pygad_space.append(values)
        gene_types.append(int if all(isinstance(v, int) for v in values) else float)
    return pygad_space, gene_types


def launch_ga_optimization(
    objective_function: ObjectiveFunction,
    optimization_settings: OptimizationSettings,
    generation_strategy: AirfoilGenerationStrategy,
    deformate_strategy: AirfoilDeformationStrategy | None = None,
    threads: int = 1,
    report_path: Path | None = None,
    config_filename: str = "optimization_settings.yaml"
) -> dict:
    """
    Запускает генетический алгоритм (PyGAD) для поиска оптимального
    аэродинамического профиля на основе заданной целевой функции.

    Функция выполняет полный цикл оптимизации:
    1. Загружает гиперпараметры ГА из YAML-файла.
    2. Парсит пространство параметров стратегии генерации.
    3. Проверяет соответствие настроек выбранной целевой функции.
    4. Инициализирует и запускает PyGAD, скрывая логику расчёта
    и перебора деформаций за функцией приспособленности.
    5. Выполняет итоговый расчёт лучшего найденного профиля.
    6. Возвращает словарь с результатами оптимизации.

    Пример использования:
        generation_strategy = AirfoilGenerationStrategy(
            generate_airfoil=lambda a, b, c: Airfoil.naca(f"{a}{b}{c:02d}"),
            parameter_space=(
                (0, 7),
                (1, 8),
                ParameterSequence(6, 15)
            )
        )

        deformate_strategy = AirfoilDeformationStrategy(
            deformate_airfoil=lambda af, angle, hinge_x: af.with_flap(angle, hinge_x),
            parameter_space=(
                ParameterSequence(5, 35, 5),
                ParameterSequence(0.75)
            )
        )

        settings = MinCruiseDragOptSettings(9, 14, 5, 9, 0.85)

        result = launch_ga_optimization(
            objective_function=ObjectiveFunction.MIN_CRUISE_DRAG,
            optimization_settings=settings,
            generation_strategy=generation_strategy,
            deformate_strategy=deformate_strategy
        )

    :param objective_function: Enum, определяющий цель оптимизации
        (например, MIN_CRUISE_DRAG).
    :param optimization_settings: Датакласс с физическими параметрами
        задачи (скорости, масса аппарата, удлинение крыла и др.).
    :param generation_strategy: Стратегия генерации исходного профиля,
        содержащая функцию генерации и пространство её параметров.
    :param deformate_strategy: Стратегия деформации профиля,
        содержащая функцию деформации и пространство её параметров.
        Если None, расчёт выполняется без деформации профиля.
    :param threads: Число потоков расчёта.
        Профили распределяются между потоками.
    :param report_path: Путь сохранения отчёта (.pdf или .md).
        Если None, отчёт не формируется.
    :param config_filename: Имя YAML-файла с настройками ГА
        (популяция, мутации, скрещивание), который лежит
        в той же директории, что и этот скрипт.

    :return: Словарь с результатами оптимизации:
            1. genes (list): Лучшая комбинация генов.
            2. fitness (float): Лучшее значение функции приспособленности.
            3. result (MinCruiseDragResult): Результат аэродинамического
                расчёта оптимального профиля, содержащий:
                    - airfoil: Исходный профиль.
                    - drag_X: Размерное сопротивление на крейсере (Н).
                    - cd_clmax_ratio: Отношение Cd_cruise / Cl_max.
                    - best_cl_max: Cl_max оптимальной конфигурации.
                    - best_deformation: Оптимальные параметры деформации.
            4. ga_instance (pygad.GA): Объект PyGAD для анализа
                сходимости и построения графиков.
    :rtype: dict

    :raises FileNotFoundError: Если файл конфигурации не найден.
    :raises TypeError: Если тип optimization_settings не соответствует
                    выбранной целевой функции.
    :raises NotImplementedError: Если целевая функция не реализована.
    :raises RuntimeError: Если ни одна особь не дала валидного результата.
    """
    if not isinstance(threads, int) or threads < 1:
        raise ValueError("threads должен быть целым числом не меньше 1")
    config_path = Path(__file__).parent / config_filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Файл настроек не найден: {config_path}")
        
    ga_settings = _load_settings(config_path)['genetic_algorithm']
    
    pygad_space, gene_types = parse_gene_space(generation_strategy.parameter_space)

    if objective_function == ObjectiveFunction.MIN_CRUISE_DRAG:
        if not isinstance(optimization_settings, MinCruiseDragOptSettings):
            raise TypeError("Несоответствие настроек и целевой функции")
    else:
        raise NotImplementedError(
            f"Целевая функция {objective_function} не реализована"
        )
    fitness_func = make_fitness_function(
        opt_settings=optimization_settings,
        objective_function=objective_function,
        generation_strategy=generation_strategy,
        deformate_strategy=deformate_strategy
    )
    # Инициализация PyGAD
    ga_instance = pygad.GA(
        fitness_func=fitness_func,
        num_genes=len(pygad_space),
        gene_space=pygad_space,
        gene_type=gene_types,

        num_generations=ga_settings['num_generations'],
        num_parents_mating=ga_settings['num_parents_mating'],
        
        sol_per_pop=ga_settings['sol_per_pop'],
        
        parent_selection_type=ga_settings['parent_selection_type'],
        K_tournament=ga_settings['K_tournament'],
        keep_elitism=ga_settings['keep_elitism'],
        crossover_type=ga_settings['crossover_type'],
        crossover_probability=ga_settings['crossover_probability'],
        mutation_type=ga_settings['mutation_type'],
        mutation_probability=ga_settings['mutation_probability'],
        mutation_by_replacement=ga_settings['mutation_by_replacement'],
        
        stop_criteria=ga_settings['stop_criteria'],
        random_seed=ga_settings.get('seed'),

        parallel_processing=["thread", threads] if threads > 1 else None,

        save_best_solutions=True,
    )
    ga_instance.run()

    # Глобальный победитель
    best_idx = max(
        range(len(ga_instance.best_solutions_fitness)),
        key=lambda i: ga_instance.best_solutions_fitness[i]
    )

    solution = ga_instance.best_solutions[best_idx]
    solution_fitness = ga_instance.best_solutions_fitness[best_idx]

    if solution_fitness <= 0:
        raise RuntimeError("Ни один расчёт не завершился успешно")

    genes = [g.item() if hasattr(g, "item") else g for g in solution]

    _, result = fitness_func.cache[tuple(genes)].result()

    # Формирование отчёта
    if report_path is not None:
        generation_results = []

        for solution in ga_instance.best_solutions:
            key = tuple(
                g.item() if hasattr(g, "item") else g
                for g in solution
            )

            value, generation_result = fitness_func.cache[key].result()

            generation_results.append(
                generation_result if value > 0 else None
            )

        generate_ga_report(
            best_result=result,
            generation_results=generation_results,
            objective_function=objective_function,
            path=Path(report_path)
        )

    return {
        "genes": genes,
        "fitness": solution_fitness,
        "result": result,
        "ga_instance": ga_instance
    }
