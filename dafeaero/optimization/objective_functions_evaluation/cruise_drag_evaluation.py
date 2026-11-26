import math

import pandas as pd

from ...facade.airfoil import Airfoil
from ... import aerodynamics, aeroconsts
from ..optimization_definition import MinCruiseDragOptSettings, MinCruiseDragResult

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
    af: "Airfoil", 
    settings: MinCruiseDragOptSettings, 
    cl_max_flap: float
) -> float | None:
    """Считает размерное сопротивление X (Н) на крейсерской скорости."""
    # 1. Находим площадь крыла и хорду (исходя из взлетного режима)
    wing_area = (2 * settings.mass * aeroconsts.g) / (aeroconsts.rho0 * settings.v_stall**2 * cl_max_flap)
    chord = math.sqrt(wing_area / settings.aspect_ratio)
    
    # 2. Потребный Cl на крейсере (вес тот же, площадь та же)
    cl_cruise = (2 * settings.mass * aeroconsts.g) / (aeroconsts.rho0 * settings.v_cruise**2 * wing_area)
    
    try:
        # 3. Получаем поляру чистого профиля на крейсерском Re
        re_cruise = aerodynamics.re(settings.v_cruise, chord)
        mach_cruise = aerodynamics.mach(settings.v_cruise, aeroconsts.a0)
        polar = af.polar(re_cruise, mach_cruise)
        
        if cl_cruise > polar.cl_max:
            return None  # Сваливание на крейсере
            
        cd_profile = polar.cd_at_cl(cl_cruise)
    except ValueError:
        return None
        
    # 4. Суммарный коэффициент сопротивления (профиль + индуктивное)
    cd_induced = (cl_cruise**2) / (math.pi * settings.aspect_ratio * settings.oswald_efficiency)
    cd_total = cd_profile + cd_induced
    
    # 5. Размерное сопротивление в Ньютонах (X = q * S * Cd)
    dynamic_pressure = 0.5 * aeroconsts.rho0 * settings.v_cruise**2
    drag_X = dynamic_pressure * wing_area * cd_total
    
    return drag_X


def evaluate_airfoil_drag(
    af: "Airfoil", 
    settings: MinCruiseDragOptSettings
    ) -> MinCruiseDragResult:
    """Целевая функция для оценки сопротивления профиля на крейсере.
    
    Перебирает положения шарнира и углы закрылка, находит конфигурацию
    с максимальным Cl_max, после чего вычисляет сопротивление на крейсере.
    """
    scan_data = []
    best_cl_max = -1.0
    best_flap_angle = None
    best_hinge_x = None

    # 1. Перебор конфигураций закрылка (шарниры x углы)
    flap = settings.flap_settings
    hinges = flap.hinge_positions if flap is not None else [0.0]
    angles = flap.angles if flap is not None else [0]
    for hinge_x in hinges:
        for angle in angles:
            try:
                # Если угол 0, закрылок не отклоняем (берем чистый профиль)
                flapped_af = af.with_flap(angle, hinge_x) if angle != 0 else af
                
                cl_max, re_stall = _calc_stall_cl(
                    flapped_af, 
                    settings.v_stall, 
                    settings.aspect_ratio, 
                    settings.mass
                )
                
                # Сохраняем точку в таблицу
                scan_data.append({
                    "Hinge_x/c": hinge_x,
                    "Flap_Angle_deg": angle,
                    "Cl_max": cl_max,
                    "Re_stall": re_stall
                })
                
                # Обновляем рекорд
                if cl_max > best_cl_max:
                    best_cl_max = cl_max
                    best_flap_angle = angle
                    best_hinge_x = hinge_x
                    
            except Exception:
                # Если XFOIL упал на этой конфигурации, пропускаем её
                continue

    # Превращаем список словарей в DataFrame
    scan_df = pd.DataFrame(scan_data)

    # 2. Если ни одна конфигурация не посчиталась (XFOIL везде упал)
    if scan_df.empty:
        return MinCruiseDragResult(
            airfoil=af, drag_X=None, best_flap_angle=None, 
            best_hinge_x=None, best_cl_max=None, scan_df=scan_df
        )

    # 3. Считаем сопротивление на крейсере для лучшей найденной конфигурации
    drag_X = _calc_cruise_drag(af, settings, best_cl_max)
    
    # 4. Возвращаем результат
    return MinCruiseDragResult(
        airfoil=af, 
        drag_X=drag_X, 
        best_flap_angle=best_flap_angle, 
        best_hinge_x=best_hinge_x, 
        best_cl_max=best_cl_max, 
        scan_df=scan_df
    )
