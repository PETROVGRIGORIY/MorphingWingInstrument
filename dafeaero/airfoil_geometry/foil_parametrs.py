from pathlib import Path

import numpy as np
_CHORD_GRID_POINTS = 2001   # число точек общей сетки по хорде


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


def airfoil_area(filename: str) -> float:
    """Расчитывает площадь аэродинамического профиля
    по формуле шнуровки.
    filename - путь до файла с геометрией профиля"""

    points = parse_foil_file(filename)
    n = len(points)
    twice_area = 0.0
    for i in range(n):
        x_prev, y_prev = points[i - 1]
        x, y = points[i]
        twice_area += x_prev * y - x * y_prev
    return 0.5 * abs(twice_area)


def airfoil_perimeter(filename: str) -> float:
    '''Расчитывает периметр аэродинамического профиля.
    filename - путь до файла с геометрией профиля'''

    points = parse_foil_file(filename)
    n = len(points)
    perimeter = 0.0
    for i in range(n):
        x_prev, y_prev = points[i - 1]
        x, y = points[i]
        perimeter += ((x - x_prev) ** 2 + (y - y_prev) ** 2) ** 0.5
    return perimeter


def normalize(coords: np.ndarray) -> np.ndarray:
    """Приводит контур к системе хорды: носок профиля в (0, 0), задняя кромка в (1, 0)"""
    pts = np.asarray(coords, dtype=float)
    te = 0.5 * (pts[0] + pts[-1])
    le = pts[np.argmax(np.linalg.norm(pts - te, axis=1))]
    chord_vec = te - le
    chord = float(np.linalg.norm(chord_vec))
    if chord == 0.0:
        raise ValueError("Нулевая длина хорды: контур вырожден")
    c, s = chord_vec / chord                       # косинус и синус угла хорды
    d = pts - le
    x = (d[:, 0] * c + d[:, 1] * s) / chord
    y = (-d[:, 0] * s + d[:, 1] * c) / chord
    return np.column_stack([x, y])


def _on_grid(surface: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Интерполирует координаты поверхности (x, y) на заданную сетку x"""
    order = np.argsort(surface[:, 0], kind="stable")
    return np.interp(x, surface[order, 0], surface[order, 1])


def _surfaces(coords: np.ndarray):
    """Возвращает (x, y_верх, y_низ) на общей косинусной сетке"""
    pts = normalize(coords)
    i_le = int(np.argmin(pts[:, 0]))
    upper = pts[: i_le + 1]      # от задней кромки к носику
    lower = pts[i_le:]           # от носика к задней кромке
    x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, _CHORD_GRID_POINTS)))
    yu, yl = _on_grid(upper, x), _on_grid(lower, x)
    if yu.mean() < yl.mean():    # контур задан в обратном порядке обхода
        yu, yl = yl, yu
    return x, yu, yl


def _extremum(x: np.ndarray, v: np.ndarray, i: int) -> tuple[float, float]:
    """Уточняет экстремум параболой по трём точкам вокруг индекса i.
    Возвращает (значение, положение x)."""
    if 0 < i < len(x) - 1:
        a, b, c = np.polyfit(x[i - 1:i + 2], v[i - 1:i + 2], 2)
        if a != 0.0:
            xv = -b / (2.0 * a)
            if x[i - 1] <= xv <= x[i + 1]:
                return float(np.polyval((a, b, c), xv)), float(xv)
    return float(v[i]), float(x[i])


def max_thickness(coords: np.ndarray) -> tuple[float, float]:
    """Максимальная относительная толщина и её положение по хорде.
    Возвращает (t/c, x/c). Толщина: разность поверхностей по вертикали
    в системе хорды."""
    x, yu, yl = _surfaces(coords)
    t = yu - yl
    return _extremum(x, t, int(np.argmax(t)))


def max_camber(coords: np.ndarray) -> tuple[float, float]:
    """Максимальная относительная кривизна средней линии и её положение.
    Возвращает (f/c, x/c); знак положительный, если средняя линия выше хорды.
    Для симметричного профиля возвращает (0.0, 0.0)."""
    x, yu, yl = _surfaces(coords)
    f = 0.5 * (yu + yl)
    value, pos = _extremum(x, f, int(np.argmax(np.abs(f))))
    if abs(value) < 1e-6:
        return 0.0, 0.0
    return value, pos
