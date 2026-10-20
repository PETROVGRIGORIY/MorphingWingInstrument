import math


# Подъёмная сила
def Y_from_Cl(
    Cl: float,
    velocity: float | int,
    wing_area: float | int,
    air_density: float | int = 1.225,
) -> float:
    """Вычисляет подъёмную силу по коэффициенту подъёмной силы.
    Cl - коэффициент подъёмной силы Cy.
    velocity - скорость полёта.
    wing_area - характерная площадь (обычно площадь крыла).
    air_density - плотность воздуха (по умолчанию 1.225).
    """
    return 0.5 * air_density * velocity ** 2 * wing_area * Cl


def Cl_from_Y(
    Y: float | int,
    velocity: float | int,
    wing_area: float | int,
    air_density: float | int = 1.225,
) -> float:
    """Вычисляет коэффициент подъёмной силы по известной подъёмной силе.
    Y - подъёмная сила Y.
    velocity - скорость полёта.
    wing_area - характерная площадь (обычно площадь крыла).
    air_density - плотность воздуха (по умолчанию 1.225).
    """
    return 2 * Y / (air_density * velocity ** 2 * wing_area)


def Cl_required(
    velocity: float | int,
    wing_area: float | int,
    mass: float | int,
    air_density: float | int = 1.225,
    gravity: float = 9.81
) -> float:
    """Вычисляет коэффициент подъёмной силы, необходимый для горизонтального полёта.
    velocity - скорость полёта.
    wing_area - характерная площадь.
    mass - масса (взлётная масса).
    air_density - плотность воздуха (по умолчанию 1.225).
    gravity - ускорение свободного падения (по умолчанию 9.81)
    """
    return 2 * mass * gravity / (air_density * velocity ** 2 * wing_area)


# Сопротивление
def X_from_Cd(
    Cd: float,
    velocity: float | int,
    reference_area: float | int,
    air_density: float | int = 1.225,
) -> float:
    """Вычисляет силу лобового сопротивления по коэффициенту сопротивления.
    Cd - коэффициент лобового сопротивления Cx.
    velocity - скорость полёта.
    reference_area - характерная площадь (обычно площадь крыла).
    air_density - плотность воздуха (по умолчанию 1.225).
    """
    return 0.5 * air_density * velocity ** 2 * reference_area * Cd


def Cd_from_X(
    X: float | int,
    velocity: float | int,
    reference_area: float | int,
    air_density: float | int = 1.225,
) -> float:
    """Вычисляет коэффициент лобового сопротивления по известной силе сопротивления.
    X - сила лобового сопротивления X [Н].
    velocity - скорость полёта.
    reference_area - характерная площадь (обычно площадь крыла).
    air_density - плотность воздуха (по умолчанию 1.225).
    """
    return 2 * X / (air_density * velocity ** 2 * reference_area)


def Cd_induced(
    Cl: float,
    aspect_ratio: float,
    oswald_efficiency: float = 0.9,
) -> float:
    """Вычисляет коэффициент индуктивного сопротивления по теории несущей линии.
    Cl - коэффициент подъёмной силы CL.
    aspect_ratio - удлинение крыла AR.
    oswald_efficiency - число (коэффициент) Освальда в формуле индуктивного
        сопротивления по теории несущей линии; зависит от формы крыла в плане
        (по умолчанию 0.9).
    """
    return Cl ** 2 / (math.pi * oswald_efficiency * aspect_ratio)


# Аэродинамическое качество
def aerodynamic_efficiency(
    Cl: float,
    Cd: float,
) -> float:
    """Вычисляет аэродинамическое качество K = Y / X = CL / CD.
    Cl - коэффициент подъёмной силы Cy.
    Cd - коэффициент лобового сопротивления Cx.
    """
    return Cl / Cd
