from enum import StrEnum
from dataclasses import dataclass
from abc import ABC

import pandas as pd

from ..facade.airfoil import Airfoil
from ..service.parametr_sequence import ParameterSequence


class ObjectiveFunction(StrEnum):
    """Целевые функции для задач оптимизации"""
    MIN_CRUISE_DRAG = "min_drag"      # Минимальное сопротивление на крейсере
    MAX_ENDURANCE = "max_endurance"   # Максимальное время барражирования (Cy^1.5 / Cx)
    MAX_RANGE = "max_range"           # Максимальная дальность K*V, K - аэродинамическое качество


class OptimizationSettings(ABC):
    """абстрактный класс настроек оптимизации"""
    pass


@dataclass(frozen=True)
class OptimizationFlapSettings:
    """Класс, который несёт информацию о том, какие углы закрылка и
    положения шарнира перебирать при решении задач оптимизации"""
    angles: ParameterSequence
    hinge_positions: ParameterSequence


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
    flap_settings: OptimizationFlapSettings | None = None


@dataclass
class MinCruiseDragResult:
    """Класс с результами расчёта сопротивления на крейсерской скорости"""
    airfoil: Airfoil
    drag_X: float | None             # Сопротивление (None, если свалился)
    best_flap_angle: float | None         # Лучший угол закрылка
    best_hinge_x: float | None       # Лучшее положение шарнира
    best_cl_max: float | None        # Cy_max при лучшем угле
    scan_df: pd.DataFrame            # Таблица расчетов (углы, Cy, Re)
