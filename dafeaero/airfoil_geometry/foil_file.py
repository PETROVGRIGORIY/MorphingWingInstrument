from pathlib import Path

import numpy as np


def write_foil_file(path: str | Path, coords: np.ndarray, name: str = "airfoil") -> None:
    """Пишет контур в формате Selig: первая строка - название, далее пары x y."""
    np.savetxt(path, coords, fmt="%.8f", header=name, comments="")


def parse_foil_file(path: str | Path) -> np.ndarray:
    """Читает контур профиля в формате Selig из .dat:
    строки из двух чисел; строка названия пропускается."""
    points = []
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            points.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    return np.array(points)
