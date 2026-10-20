from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True) #frozen для хеширования
class Airfoil:
    name: str
    path: Path


@dataclass(frozen=True) #frozen для хеширования
class AnglesOfAttackSequence:
    """Последовательность углов для проведения расчётов.
    alpha_first - Начальный угол атаки (может быть отрицательным).
    alpha_last - Конечный угол атаки.
    step - Шаг изменения угла атаки (всегда задаётся положительным числом)"""
    
    alpha_first: int | float
    alpha_last: int | float
    step: int | float
