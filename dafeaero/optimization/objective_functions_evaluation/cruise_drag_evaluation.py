import math
from itertools import product

from ...facade.airfoil import Airfoil
from ... import aerodynamics, aeroconsts
from ..optimization_definition import (
    MinCruiseDragOptSettings, MinCruiseDragResult, AirfoilDeformationStrategy
)
# Константы сходимости
STALL_CL_ITERATIONS = 5
STALL_CL_TOLERANCE = 1e-3


def _calc_stall_cl(
    af: Airfoil, 
    v_stall: float, 
    aspect_ratio: float, 
    mass: float
) -> tuple[float, float]:
    """Итеративно находит Cl_max и Re на скорости сваливания."""
    mach_stall = aerodynamics.mach(v_stall, aeroconsts.a0)
    cl_max_estimate = 1.5  # Начальное приближение (с закрылком)
    re_stall = 0.0
    
    for _ in range(STALL_CL_ITERATIONS):
        # 1. Площадь крыла из условия сваливания
        wing_area = (2 * mass * aeroconsts.g) / (aeroconsts.rho0 * v_stall**2 * cl_max_estimate)
        chord = math.sqrt(wing_area / aspect_ratio)
        
        # 2. Число Рейнольдса
        re_stall = aerodynamics.re(v_stall, chord)
        
        # 3. Уточненный Cl_max
        cl_max_new = af.polar(re_stall, mach_stall).cl_max
        
        if abs(cl_max_new - cl_max_estimate) < STALL_CL_TOLERANCE:
            return cl_max_new, re_stall
            
        cl_max_estimate = cl_max_new
        
    return cl_max_estimate, re_stall


def _calc_cruise_drag(
    af: Airfoil,
    settings: MinCruiseDragOptSettings,
    cl_max_stall: float
) -> tuple[float, float] | None:
    """Вычисляет размерное сопротивление и параметр Cd_cruise / Cl_max."""

    wing_area = (
        2 * settings.mass * aeroconsts.g
        / (aeroconsts.rho0 * settings.v_stall**2 * cl_max_stall)
    )

    chord = math.sqrt(wing_area / settings.aspect_ratio)

    cl_cruise = (
        2 * settings.mass * aeroconsts.g
        / (aeroconsts.rho0 * settings.v_cruise**2 * wing_area)
    )

    try:
        re_cruise = aerodynamics.re(settings.v_cruise, chord)
        mach_cruise = aerodynamics.mach(
            settings.v_cruise, aeroconsts.a0
        )

        polar = af.polar(re_cruise, mach_cruise)

        if cl_cruise > polar.cl_max:
            return None

        cd_profile = polar.cd_at_cl(cl_cruise)

    except ValueError:
        return None

    cd_induced = cl_cruise**2 / (
        math.pi * settings.aspect_ratio
        * settings.oswald_efficiency
    )

    cd_total = cd_profile + cd_induced

    dynamic_pressure = 0.5 * aeroconsts.rho0 * settings.v_cruise**2

    drag_X = dynamic_pressure * wing_area * cd_total
    cd_clmax_ratio = cd_total / cl_max_stall

    return drag_X, cd_clmax_ratio


def evaluate_airfoil_drag(
    af: Airfoil,
    settings: MinCruiseDragOptSettings,
    deformate_strategy: AirfoilDeformationStrategy | None = None
) -> MinCruiseDragResult:
    """Находит деформацию, минимизирующую сопротивление на крейсере."""

    best_drag_X = None
    best_cd_clmax_ratio = None
    best_cl_max = None
    best_deformation = None

    parameter_space = (
        deformate_strategy.parameter_space
        if deformate_strategy is not None
        else ()
    )

    for params in product(*parameter_space):
        try:
            # Деформация профиля
            deformed_af = (
                deformate_strategy.deformate_airfoil(af, *params)
                if deformate_strategy is not None
                else af
            )

            # Расчёт деформированного профиля на сваливании
            cl_max, _ = _calc_stall_cl(
                deformed_af,
                settings.v_stall,
                settings.aspect_ratio,
                settings.mass
            )

            if not math.isfinite(cl_max) or cl_max <= 0:
                continue

            # Расчёт основного профиля на крейсере
            result = _calc_cruise_drag(af, settings, cl_max)

            if result is None:
                continue

            drag_X, cd_clmax_ratio = result

            if not math.isfinite(drag_X) or drag_X <= 0:
                continue

            # Обновление оптимальной конфигурации
            if best_drag_X is None or drag_X < best_drag_X:
                best_drag_X = drag_X
                best_cd_clmax_ratio = cd_clmax_ratio
                best_cl_max = cl_max
                best_deformation = params

        except Exception:
            continue

    return MinCruiseDragResult(
        airfoil=af,
        drag_X=best_drag_X,
        cd_clmax_ratio=best_cd_clmax_ratio,
        best_cl_max=best_cl_max,
        best_deformation=best_deformation
    )
