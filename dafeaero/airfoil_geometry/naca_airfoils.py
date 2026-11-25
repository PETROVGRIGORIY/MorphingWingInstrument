"""Генерация координат профилей NACA средствами XFOIL."""
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..config import XFOIL_EXE_PATH
from ..xfoilpy.run_xfoil import run_xfoil
from .foil_file import parse_foil_file


@lru_cache(maxsize=128)
def generate_naca(code: str | int, n_points: int = 161) -> np.ndarray:
    """Контур профиля NACA (4 или 5 цифр), сгенерированный XFOIL.
    code - цифровой код, например "2412"; n_points - число панелей (точек контура).
    Возвращает массив (N, 2) в порядке XFOIL (от задней кромки по верхней
    поверхности к носику и обратно по нижней)."""

    if isinstance(code, int):
        code = str(code)
        # Если код короче 4 символов, добавляем ведущие нули (например, 12 -> "0012")
        if len(code) < 4:
            code = code.zfill(4)

    if not (code.isdigit() and len(code) in (4, 5)):
        raise ValueError(
            f"XFOIL генерирует только 4- и 5-значные профили NACA, получено {code!r}")

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        commands = (
            f"naca {code}\n"
            f"pane\n"
            f"ppar\n"
            f"n {n_points}\n"
            f"\n"
            f"\n"
            f"psav naca.dat\n"
            f"quit\n"
        )
        cmd_file = work_dir / "commands.in"
        cmd_file.write_text(commands)

        run_xfoil(cmd_file, XFOIL_EXE_PATH, work_dir)

        saved = work_dir / "naca.dat"
        if not saved.exists():
            raise RuntimeError(f"XFOIL не сохранил профиль NACA {code}")
        coords = parse_foil_file(saved)

    if len(coords) < 5:
        raise RuntimeError(f"Не удалось прочитать контур профиля NACA {code}")
    return coords.copy()
