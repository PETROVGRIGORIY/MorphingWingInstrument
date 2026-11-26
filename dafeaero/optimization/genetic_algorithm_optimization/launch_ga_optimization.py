import yaml
import pygad

import logging
from pathlib import Path

from typing import Callable

from ..optimization_definition import (
    ObjectiveFunction, OptimizationSettings, MinCruiseDragOptSettings
)
from .ga_components.fitness_evaluator import make_fitness_function
from ...service.parametr_sequence import ParameterSequence
from ...facade.airfoil import Airfoil

logger = logging.getLogger(__name__)


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
    generate_airfoil: Callable[..., Airfoil],
    gene_space: tuple[list|tuple|ParameterSequence, ...],
    deformate_airfoil,
    config_filename: str = "optimization_settings.yaml"
) -> dict:
    """
    Запускает генетический алгоритм (PyGAD) для поиска оптимального 
    аэродинамического профиля на основе заданной целевой функции.
    
    Функция выполняет полный цикл оптимизации:
    1. Загружает гиперпараметры ГА из YAML-файла.
    2. Парсит пространство генов и определяет их типы (int или float).
    3. Проверяет соответствие переданных настроек выбранной целевой функции.
    4. Инициализирует и запускает PyGAD, скрывая логику расчета за функцией фитнеса.
    5. Возвращает словарь с лучшим найденным решением.
    
    Пример использования:
        gene_space = (
            (0, 7),                     # кривизна NACA
            (1, 8),                     # положение кривизны
            ParameterSequence(6, 15)    # толщина
        )
        settings = MinCruiseDragOptSettings(9, 14, 5, 9, 0.85)
        
        result = launch_ga_optimization(
            generate_airfoil=lambda a,b,c: Airfoil.naca(f"{a}{b}{c:02d}"),
            gene_space=gene_space,
            objective_function=ObjectiveFunction.MIN_CRUISE_DRAG,
            optimization_settings=settings
        )

    :param generate_airfoil: Функция-фабрика, которая принимает значения генов 
        (например, параметры NACA) и возвращает готовый объект Airfoil.
    :param gene_space: Кортеж, содержащий описания генов. Каждый элемент может быть:
        - list: явный список допустимых значений.
        - tuple из 2 элементов: диапазон [min, max]. 
        - ParameterSequence: объект, содержащий последовательность значений.
    :param objective_function: Enum, определяющий цель оптимизации 
        (например, MIN_CRUISE_DRAG).
    :param optimization_settings: Датакласс с физическими параметрами среды 
        (скорости, масса, удлинение крыла) и настройками перебора механизации.
    :param config_filename: Имя YAML-файла с настройками ГА (популяция, мутации, 
        скрещивание), который лежит в той же директории, что и этот скрипт.
    
    :return: Словарь с результатами оптимизации:
             1. genes (list): Лучшая комбинация генов.
             2. airfoil (Airfoil): Объект профиля, созданный из лучших генов.
             3. fitness (float): Лучшее значение функции приспособленности.
             4. drag_X (float): Вычисленное сопротивление (в Ньютонах).
             5. ga_instance (pygad.GA): Объект PyGAD для анализа сходимости и графиков.
    :rtype: dict
    
    :raises FileNotFoundError: Если файл конфигурации `config_filename` не найден.
    :raises TypeError: Если тип `optimization_settings` не соответствует выбранной 
                       `objective_function`.
    :raises RuntimeError: Если ни одна особь за все поколения не дала валидного 
                          результата (fitness = 0 для всей популяции).
    """
    config_path = Path(__file__).parent / config_filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Файл настроек не найден: {config_path}")
        
    ga_settings = _load_settings(config_path)['genetic_algorithm']
    
    pygad_space, gene_types = parse_gene_space(gene_space)

    if objective_function == ObjectiveFunction.MIN_CRUISE_DRAG:
        if not isinstance(optimization_settings, MinCruiseDragOptSettings):
            raise TypeError("Несответствие настроек и целевой функции")
    fitness_func = make_fitness_function(
        generate_airfoil, optimization_settings, objective_function)

    # Инициализация PyGAD
    logger.info("Инициализация Генетического Алгоритма...")
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
        
        # parallel_processing=['process', ga_settings['threads']], # Пока выключено
        logger=logger
    )

    # Запуск оптимизации
    logger.info("--- СТАРТ ОПТИМИЗАЦИИ ---")
    ga_instance.run()
    
    # Сбор результатов
    solution, solution_fitness, _ = ga_instance.best_solution()
    if solution_fitness <= 0:
        raise RuntimeError("Ни один расчёт не завершился успешно (fitness = 0): смотрите лог")
    genes = [g.item() if hasattr(g, "item") else g for g in solution]

    return {
        "genes": genes,
        "airfoil": generate_airfoil(*genes),
        "fitness": solution_fitness,
        "drag_X": 1.0 / solution_fitness - 1e-6,
        "ga_instance": ga_instance,
    }
