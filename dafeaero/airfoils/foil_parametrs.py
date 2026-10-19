from pathlib import Path


def parse_foil_file(filename: str) -> list[tuple[float, float]]:
    """Возвращает список точек из файла с геометрией профиля.
    filename - путь до файла с геометрией профиля"""

    path = Path(filename)
    with path.open("r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    points: list[tuple[float, float]] = []
    for lineno, line in enumerate(lines[1:], start=2):
        parts = line.split()
        if not parts:
            continue
        if len(parts) < 2:
            raise ValueError(
                f"{path}: строка {lineno}: ожидались 2 числа, получено {parts!r}"
            )
        try:
            x, y = float(parts[0]), float(parts[1])
        except ValueError as exc:
            raise ValueError(
                f"{path}: строка {lineno}: не удалось разобрать {parts!r}"
            ) from exc
        points.append((x, y))

    if not points:
        raise ValueError(f"{path}: не найдено ни одной точки профиля")

    return points


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
