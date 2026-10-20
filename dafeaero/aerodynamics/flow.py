import math
R_AIR = 287.05  # удельная газовая постоянная воздуха


def Re(
    velocity: float | int,
    length: float | int,
    kinematic_viscosity: float | int = 1.5e-5,
    ) -> int:
    """Вычисляет число Рейнольдса.
    velocity - скорость потока.
    length - характерный линейный размер.
    kinematic_viscosity - кинематическая вязкость (по умолчанию 1.5e-5).
    Возвращает число Рейнольдса, приведённое к int.
    """
    return int(velocity * length / kinematic_viscosity)


def speed_of_sound(
    temperature: float | int,
    gamma: float = 1.4,
    gas_constant: float = R_AIR,
) -> float:
    """Вычисляет скорость звука в газе.
    temperature - температура газа [К].
    gamma - отношение удельных теплоёмкостей (по умолчанию 1.4 для воздуха).
    gas_constant - удельная газовая постоянная [Дж/(кг·К)]
        (по умолчанию 287.05 для воздуха).
    Возвращает скорость звука a [м/с].
    """
    return math.sqrt(gamma * gas_constant * temperature)


def M(
    velocity: float | int,
    speed_of_sound: float | int,
) -> float:
    """Вычисляет число Маха.
    velocity - скорость потока (или тела) [м/с].
    speed_of_sound - скорость звука в среде [м/с].
    """
    return velocity / speed_of_sound
