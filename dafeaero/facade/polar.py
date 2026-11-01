"""Результат расчёта поляры аэродинамического профиля"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

_REQUIRED_COLS = ("alpha", "CL", "CD")
#минимальный набор столбцов поляры
_SUPPORTED_COLS = ("alpha", "CL", "CD", "CDp", "CM", "Top_Xtr", "Bot_Xtr")
#полный набор столбцов поляры xfoil


def _check_range(value: float, lower: float, upper: float, what: str) -> None:
    """Проверяет, что значение находится в заданном замкнутом диапазоне [lower, upper]"""
    if not (lower <= value <= upper):
        raise ValueError(
            f"{what} = {value:g} вне диапазона поляры [{lower:g}, {upper:g}]"
        )


class Polar:
    """Результат расчёта поляры профиля при фиксированных Re и M"""

    __slots__ = ("_df", "_Re", "_M", "_airfoil_name", "_solver", "_solver_options")

    def __init__(
        self,
        data: pd.DataFrame,
        *,
        Re: float,
        M: float = 0.0,
        airfoil_name: str = "",
        solver: str = "",
        solver_options: Mapping[str, Any] | None = None,
    ):
        missing = [c for c in _REQUIRED_COLS if c not in data.columns]
        if missing:
            raise ValueError(f"В данных поляры нет колонок: {missing}")

        cols = [c for c in _SUPPORTED_COLS if c in data.columns]
        df = (
            data[cols]
            .dropna(subset=list(_REQUIRED_COLS))
            .drop_duplicates(subset="alpha")
            .sort_values("alpha")
            .reset_index(drop=True)
        )
        if df.empty:
            raise ValueError("Поляра не содержит ни одной сошедшейся точки")

        self._df = df
        self._Re = float(Re)
        self._M = float(M)
        self._airfoil_name = airfoil_name
        self._solver = solver
        self._solver_options = MappingProxyType(dict(solver_options or {}))

    # условия расчёта
    @property
    def Re(self) -> float: return self._Re
    @property
    def M(self) -> float: return self._M
    @property
    def airfoil_name(self) -> str: return self._airfoil_name
    @property
    def solver(self) -> str: return self._solver
    @property
    def options(self) -> Mapping[str, Any]: return self._solver_options

    def _get_column_copy(self, name: str) -> np.ndarray:
        return self._df[name].to_numpy(dtype=float, copy=True)

    @property
    def alpha(self) -> np.ndarray: return self._get_column_copy("alpha")
    @property
    def cl(self) -> np.ndarray: return self._get_column_copy("CL")
    @property
    def cd(self) -> np.ndarray: return self._get_column_copy("CD")

    def to_dataframe(self) -> pd.DataFrame:
        """Копия таблицы с колонками XFOIL: alpha, CL, CD, CDp, CM, Top_Xtr, Bot_Xtr"""
        return self._df.copy()

    def __len__(self) -> int:
        return len(self._df)

    # характерные точки
    @property
    def cl_max(self) -> float:
        return float(self._df["CL"].max())

    @property
    def stall_alpha(self) -> float:
        """Угол атаки (alpha), при котором достигается максимальный коэффициент 
        подъёмной силы (CL_max). Соответствует началу срыва потока"""
        cl = self._get_column_copy("CL")
        alpha = self._get_column_copy("alpha")
        return float(alpha[np.argmax(cl)])

    @property
    def cd_min(self) -> float:
        return float(self._df["CD"].min())

    @property
    def ld_max(self) -> float:
        """Максимальное аэродинамическое качество CL/CD профиля"""
        cl = self._get_column_copy("CL")
        cd = self._get_column_copy("CD")
        return float(np.max(cl / cd))

    @property
    def ld_max_alpha(self) -> float:
        """Угол атаки, при котором достигается максимальное 
        аэродинамическое качество"""
        cl = self._get_column_copy("CL")
        cd = self._get_column_copy("CD")
        alpha = self._get_column_copy("alpha")
        return float(alpha[np.argmax(cl / cd)])

    # интерполяция
    def _pre_stall_cl(self) -> tuple[np.ndarray, np.ndarray]:
        """Возвращает точки CL до срыва и их индексы в исходном массиве"""
        cl = self._get_column_copy("CL")
        cl_u, idx = np.unique(cl[: int(np.argmax(cl)) + 1], return_index=True)
        return cl_u, idx

    def cl_at_alpha(self, alpha: float) -> float:
        """Коэффициент подъёмной силы (CL) при заданном угле атаки (alpha)"""
        a = self._get_column_copy("alpha")
        _check_range(alpha, a[0], a[-1], "alpha")
        return float(np.interp(alpha, a, self._get_column_copy("CL")))

    def cd_at_cl(self, cl: float) -> float:
        """CD при заданном CL на докритическом режиме. ValueError, если CL не достигается."""
        cl_u, idx = self._pre_stall_cl()
        _check_range(cl, cl_u[0], cl_u[-1], "CL")
        return float(np.interp(cl, cl_u, self._get_column_copy("CD")[idx]))

    def alpha_at_cl(self, cl: float) -> float:
        """Угол атаки (alpha), при котором достигается заданный CL на докритической ветви.
        Вызывает ValueError, если заданный CL не достигается на докритическом режиме"""
        cl_u, idx = self._pre_stall_cl()
        _check_range(cl, cl_u[0], cl_u[-1], "CL")
        return float(np.interp(cl, cl_u, self._get_column_copy("alpha")[idx]))

    def __repr__(self) -> str:
        a = self.alpha
        return (
            f"Polar(airfoil={self._airfoil_name!r}, Re={self._Re:.3g}, M={self._M:g}, "
            f"solver={self._solver!r}, n={len(self)}, "
            f"alpha=[{a[0]:g}, {a[-1]:g}], CLmax={self.cl_max:.3f})"
        )
