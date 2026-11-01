import tempfile
from pathlib import Path

import numpy as np

from ..config import XFOIL_EXE_PATH
from .foil_parametrs import write_foil_file, parse_foil_file
from ..xfoilpy.run_xfoil import run_xfoil


def add_flap_to_airfoil(
        coords: np.ndarray, hinge_x: float, deflection: float) -> np.ndarray:
    """Контур профиля с закрылком (средствами XFOIL, gdes → flap).
    hinge_x - положение шарнира (x/c), deflection - угол, градусы (положительный вниз).
    Важно! координата y считается xfoil по умолчанию"""

    # Вся работа XFOIL идёт во временной папке, она удаляется автоматически.
    # Профиль пишем внутрь под коротким именем, поэтому в командах только
    # относительные имена файлов: не нужны relpath и обход проблем с путями.
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        write_foil_file(work_dir / "airfoil.dat", coords)

        commands = (
            f"load airfoil.dat\n"
            f"airfoil\n"
            f"gdes\n"
            f"flap\n"
            f"{hinge_x}\n"
            f"999\n"
            f"1\n"
            f"{deflection}\n"
            f"exec\n"
            f"\n"
            f"psav flapped.dat\n"
            f"quit\n"
        )
        cmd_file = work_dir / "commands.in"
        cmd_file.write_text(commands)

        run_xfoil(cmd_file, XFOIL_EXE_PATH, work_dir)

        saved_foil = work_dir / "flapped.dat"
        if not saved_foil.exists():
            raise RuntimeError("XFOIL не сохранил профиль с закрылком")

        result = parse_foil_file(saved_foil)

    if len(result) < 5:
        raise RuntimeError("Не удалось прочитать контур профиля с закрылком")
    return result
