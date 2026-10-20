import math
from pathlib import Path
import dafeaero as da


def objective_cd_cruise(
    V_cruise: int | float,
    V_stall: int | float,
    AR: int | float,
    mass: int | float,
    af_characteristics: da.xfoilpy.AirfoilCharacteristics,
    inducted: bool
    ):
    
    density = 1.225
    g = 9.81

    M_cruise = da.aerodynamics.M(V_cruise, 343)
    M_stall = da.aerodynamics.M(V_stall, 343)

    cy_max_estimate = 1.2 
    l = 1.0
    # Re_stall = 100000

    for _ in range(4):
        S = (2 * mass * g) / (density * V_stall**2 * cy_max_estimate)
        l = math.sqrt(S / AR)
        print(l)
        Re_stall = da.aerodynamics.Re(V_stall, l)
        print(Re_stall)
        
        cy_max_exact = af_characteristics.Cl_max(Re_stall, M_stall)
        print("Расчёт проведён")
        if cy_max_exact is None:
            return None
        cy_max_estimate = cy_max_exact

    Re_cruise = da.aerodynamics.Re(V_cruise, l)
    cy_max = af_characteristics.Cl_max(Re_stall, M_stall)
    cy_cruise = cy_max * (V_stall / V_cruise)**2
    
    cx_airfoil = af_characteristics.get_Cd_from_Cl(Re_cruise, M_cruise, cy_cruise)
    
    if cx_airfoil is None:
        return None 
        
    e_oswald = 0.85 
    if inducted:
        cx_induced = (cy_cruise**2) / (math.pi * AR * e_oswald)
        return cx_airfoil + cx_induced
    else:
        return cx_airfoil

def find_best_airfoil(   
    V_cruise: int | float,
    V_stall: int | float,
    mass: int | float,
    AR: int | float,
    ):
    folder_path = Path("dafeaero/airfoils/foildatabase/task2")
    airfoils = []

    if not folder_path.exists():
        print(f"Ошибка: Папка {folder_path} не найдена!")
        return

    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.dat']:
            airfoil_name = file_path.stem 
            airfoil = da.xfoilpy.Airfoil(airfoil_name, str(file_path))
            airfoils.append(airfoil)
            print(f"Успешно загружен: {airfoil_name}")

    print(f"\nВсего загружено профилей: {len(airfoils)}")

    best_airfoil_prof = None
    min_cd_prof = float('inf')
    
    best_airfoil_ind = None
    min_cd_ind = float('inf')

    for af in airfoils:
        print(f"Расчет профиля: {af.name}...")

        af_characteristics = da.xfoilpy.AirfoilCharacteristics(af)

        cd_prof = objective_cd_cruise(
            V_cruise, V_stall, AR, mass, af_characteristics, inducted=False
        )
        if cd_prof is not None and cd_prof < min_cd_prof:
            min_cd_prof = cd_prof
            best_airfoil_prof = af

        cd_ind = objective_cd_cruise(
            V_cruise, V_stall, AR, mass, af_characteristics, inducted=True
        )
        if cd_ind is not None and cd_ind < min_cd_ind:
            min_cd_ind = cd_ind
            best_airfoil_ind = af
    
    if best_airfoil_prof:
        print(f"\nЛучший профиль (только Cx профиля): {best_airfoil_prof.name}")
        print(f"Минимальный Cx профиля: {min_cd_prof:.6f}")
    else:
        print("\nНе удалось найти подходящий профиль.")

    if best_airfoil_ind:
        print(f"Лучший профиль (полный Cx крыла): {best_airfoil_ind.name}")
        print(f"Минимальный полный Cx: {min_cd_ind:.6f}")
    else:
        print("\nНе удалось найти подходящий профиль.")

    return best_airfoil_prof, best_airfoil_ind

find_best_airfoil(14, 9, 5, 9)