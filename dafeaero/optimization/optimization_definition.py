from enum import StrEnum
from dataclasses import dataclass
from abc import ABC
from typing import Callable

from ..facade.airfoil import Airfoil
from ..service.parametr_sequence import ParameterSequence


class OptimizationType(StrEnum):
    EXHAUSTIVE_SEARCH = "exhaustive_search"
    GENETIC_ALGORITHM = "genetic_algorithm"


class ObjectiveFunction(StrEnum):
    """Целевые функции для задач оптимизации"""
    MIN_CRUISE_DRAG = "min_drag"      # Минимальное сопротивление на крейсере
    MAX_ENDURANCE = "max_endurance"   # Максимальное время барражирования (Cy^1.5 / Cx)
    MAX_RANGE = "max_range"           # Максимальная дальность K*V, K - аэродинамическое качество


class OptimizationSettings(ABC):
    """абстрактный класс настроек оптимизации"""
    pass


class OptimizationResult(ABC):
    """абстрактный класс результата вычислений целевой функции"""
    pass


@dataclass
class AirfoilGenerationStrategy:
    generate_airfoil: Callable[..., Airfoil]
    parameter_space: tuple[list|tuple|ParameterSequence, ...]


@dataclass
class AirfoilDeformationStrategy:
    deformate_airfoil: Callable[..., Airfoil]
    parameter_space: tuple[list|ParameterSequence, ...]


# Минимизация сопротивления на крейсере
@dataclass(frozen=True)
class MinCruiseDragOptSettings(OptimizationSettings):
    """v_stall - скорость сваливания в м/c
    v_cruise - крейсерская скорость в м/c
    mass - масса летательного аппарата в кг
    aspect_ratio - удлинение крыла летательного аппарата
    """
    v_stall: int | float
    v_cruise: int | float
    mass: int | float
    aspect_ratio: int | float
    oswald_efficiency: int | float


@dataclass
class MinCruiseDragResult(OptimizationResult):
    airfoil: Airfoil
    drag_X: float | None
    cd_clmax_ratio: float | None
    best_cl_max: float | None
    best_deformation: tuple | None
