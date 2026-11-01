from __future__ import annotations

import hashlib
import tempfile
from functools import cached_property
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike

from .. import airfoil_geometry as geometry

from ..config import XFOIL_EXE_PATH
from ..xfoilpy.base_classes import AnglesOfAttackSequence
from ..xfoilpy.command_files import xfoil_command_aseq
from ..xfoilpy.parse_polar import parse_xfoil_polar
from ..xfoilpy.run_xfoil import run_xfoil
from .polar import Polar


def _as_coords(coords: ArrayLike) -> np.ndarray:
    """Копия контура как float-массив (N, 2); только проверка формы и значений."""
    arr = np.array(coords, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"Контур должен иметь форму (N, 2), получено {arr.shape}")
    if len(arr) < 5:
        raise ValueError(f"Слишком мало точек контура: {len(arr)}")
    if not np.isfinite(arr).all():
        raise ValueError("Контур содержит NaN или inf")
    return arr


class Airfoil:
    """Многофункциональный класс для работы с аэродинамическим профилем,
    способный работать с точками контура, вычислять геометрические характеристики,
    запускать расчёт аэродинамической поляры на заданном режиме.
    Хранит неизменяемый контур координат (x/c, y/c).
    
    Создание:
        Airfoil(coords, name="...")
        Airfoil.from_file("clark_y.dat")
        Airfoil.naca("2412")
    """
    _coords: np.array
    _name: str
    _digest: str
    _polars: dict[tuple, Polar]
    
    # Кешируемые свойства
    _thickness_max: tuple[float, float]
    _camber_max: tuple[float, float]


    def __init__(self, coords: ArrayLike, name: str = "unnamed"):
        c = _as_coords(coords)
        c.flags.writeable = False
        self._coords = c
        self._name = str(name)
        self._digest = hashlib.sha256(c.tobytes()).hexdigest()
        self._polars: dict[tuple, Polar] = {}

    # Альтернативные конструкторы
    @classmethod
    def from_file(cls, path: str | Path, name: str | None = None) -> Airfoil:
        """Читает профиль из .dat (формат Selig)."""
        path = Path(path)
        return cls(geometry.parse_foil_file(path), name=name or path.stem)

    @classmethod
    def naca(cls, code: str, n_points: int = 161, closed_te: bool = True) -> Airfoil:
        """Профиль NACA по цифровому коду, например Airfoil.naca("2412")."""
        return cls(geometry.naca(code, n_points, closed_te), name=f"NACA {code}")

    # Данные
    @property
    def name(self) -> str:
        return self._name

    @property
    def coords(self) -> np.ndarray:
        """Возвращает массив точек профиля (только для чтения)"""
        return self._coords

    @property
    def n_points(self) -> int:
        """Возвращает количество точек профиля"""
        return len(self._coords)

    def __array__(self, dtype=None, copy=None) -> np.ndarray:
        """Преобразует профиль в массив координат (всегда возвращает копию)"""
        arr = self._coords if dtype is None else self._coords.astype(dtype)
        return arr.copy()

    # Геометрические характеристики (в долях хорды)
    @cached_property
    def _thickness_max(self) -> tuple[float, float]:
        """Считает толщину и её позицию (результат кешируется)"""
        return geometry.max_thickness(self._coords)

    @cached_property
    def _camber_max(self) -> tuple[float, float]:
        """Считает кривизну и её позицию (результат кешируется)"""
        return geometry.max_camber(self._coords)

    @property
    def thickness(self) -> float:
        """Максимальная относительная толщина."""
        return self._thickness_max[0]

    @property
    def thickness_position(self) -> float:
        """Положение максимальной толщины по хорде (x/c)."""
        return self._thickness_max[1]

    @property
    def camber(self) -> float:
        """Максимальная относительная кривизна средней линии."""
        return self._camber_max[0]

    @property
    def camber_position(self) -> float:
        """Положение максимальной кривизны по хорде (x/c)."""
        return self._camber_max[1]

    # Преобразования (возвращают новый Airfoil)
    def normalized(self) -> Airfoil:
        """Профиль в системе хорды: носок в (0, 0), задняя кромка в (1, 0)."""
        return Airfoil(geometry.normalize(self._coords), name=self._name)

    def with_flap(self, deflection: float, hinge_x: float) -> Airfoil:
        """Возвращае класс Airfoil профиля с закрылком.
        hinge_x - положение шарнира (x/c), deflection - угол, градусы
        (положительный вниз)."""
        coords = geometry.add_flap_to_airfoil(
            self._coords, hinge_x=hinge_x, deflection=deflection
        )
        return Airfoil(coords, name=f"{self._name} (flap {deflection:g}°)")

    # Ввод/вывод
    def save(self, path: str | Path) -> Path:
        """Сохраняет профиль в .dat (формат Selig)."""
        path = Path(path)
        geometry.write_foil_file(path, self._coords, self._name)
        return path

    # Аэродинамика
    def polar(
        self,
        Re: float,
        M: float = 0.0,
        aoas: AnglesOfAttackSequence | tuple[float, float, float] = (-5, 20, 1),
        ncr: int = 9,
        max_it: int = 250,
        *,
        cache: bool = True,
    ) -> Polar:
        """Считает поляру профиля в XFOIL.

        Re, M - числа Рейнольдса и Маха; aoas - диапазон углов атаки, градусы
        (AnglesOfAttackSequence либо кортеж (начало, конец, шаг));
        ncr - параметр Ncrit; max_it - максимум итераций XFOIL.
        Повторный вызов с теми же параметрами берёт результат из кэша объекта
        (cache=False - пересчитать принудительно).
        """
        seq = aoas if isinstance(aoas, AnglesOfAttackSequence) else AnglesOfAttackSequence(*aoas)
        key = (float(Re), float(M), seq, int(ncr), int(max_it))

        if cache and key in self._polars:
            return self._polars[key]

        # Отдельная временная папка на каждый расчёт: нет конфликтов при параллельных запусках
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            dat = workdir / "airfoil.dat"
            geometry.write_foil_file(dat, self._coords, self._name)

            cmd = xfoil_command_aseq(Re, M, seq, ncr, max_it, dat, workdir)
            polar_file = run_xfoil(cmd, XFOIL_EXE_PATH, workdir)
            if not polar_file.exists():
                raise RuntimeError(
                    f"XFOIL не создал файл поляры для {self._name!r} (Re={Re:g}, M={M:g})"
                )
            df, _meta = parse_xfoil_polar(polar_file)   # читать нужно внутри with

        result = Polar(
            df, Re=Re, M=M, airfoil_name=self._name, solver="xfoil",
            solver_options={"ncrit": ncr, "max_iter": max_it},
        )
        if cache:
            self._polars[key] = result
        return result

    # Визуализация профиля
    def plot(self, show = True, ax=None, **kwargs):
        """Рисует контур профиля. Возвращает matplotlib Axes."""
        import matplotlib.pyplot as plt

        if ax is None:
            _, ax = plt.subplots(figsize=(8, 3))
        style = {"lw": 1.5, "label": self._name} | kwargs
        ax.plot(self._coords[:, 0], self._coords[:, 1], **style)
        ax.set_aspect("equal")
        ax.set_xlabel("x/c")
        ax.set_ylabel("y/c")
        ax.grid(True, ls=":")
        if show:
            plt.show()
        return ax

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Airfoil) and self._digest == other._digest

    def __hash__(self) -> int:
        return hash(self._digest)

    def __repr__(self) -> str:
        return f"Airfoil({self._name!r}, n_points={self.n_points})"
