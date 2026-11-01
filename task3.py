import math
from pathlib import Path
import dafeaero as da

import pandas as pd


TASK_DATA_PATH = Path("task3_data")
TASK3_AIRFOILS_PATH = Path("dafeaero/airfoils/foildatabase/task3")


def find_optimal_flap_angle(
    airfoil_path: str | Path,
    V_stall: float,
    AR: float,
    mass: float,
    hinge_position: float = 0.75
) -> tuple[int, float]:
    """Перебирает углы закрылка, итеративно уточняя Re для каждого."""
    density = 1.225
    g = 9.81
    foil = Path(airfoil_path)
    
    TASK_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    best_cy_max = -1.0
    best_angle = 0
    
    print(f"  Перебор углов закрылка для: {foil.name}")
    
    for angle in range(0, 36, 5): # 10, 15, 20, 25, 30, 35
        flapped_foil_path = TASK_DATA_PATH / f"{foil.stem}_flap_{angle}.dat"

        try:
            da.airfoil_geometry.add_flap_to_airfoil(
                flap_angle=angle,
                hinge_position=hinge_position,
                airfoil_path=foil,
                modified_airfoil_path=flapped_foil_path
            )
        except Exception:
            print("Не удалось перестроить геометрию")
            continue
        
        flapped_af = da.xfoilpy.Airfoil(f"{foil.stem}_flap_{angle}", flapped_foil_path)
        af_char = da.xfoilpy.AirfoilCharacteristics(flapped_af)
        
        M_stall = da.aerodynamics.mach(V_stall, 343)

        cy_max_estimate = 1.5 # Начальное приближение для закрылка
        chord = 1.0
        
        try:
            for _ in range(4):
                # 1. Находим площадь и хорду по текущей оценке Cy_max
                S = (2 * mass * g) / (density * V_stall**2 * cy_max_estimate)
                chord = math.sqrt(S / AR)
                
                # 2. Считаем Re
                Re_stall = da.aerodynamics.re(V_stall, chord)
                
                # 3. Запрашиваем новый Cy_max
                cy_max_exact = af_char.Cl_max(Re_stall, M_stall)
                if cy_max_exact is None:
                    break
                    
                cy_max_estimate = cy_max_exact
            
            # После 4 итераций cy_max_estimate содержит уточненное значение
            if cy_max_estimate > best_cy_max:
                best_cy_max = cy_max_estimate
                best_angle = angle
                print(f"    Угол {angle}°: Cy_max = {best_cy_max:.4f} (Re = {Re_stall:.0f})")
            else:
                print(f"    Угол {angle}°: Cy_max = {cy_max_estimate:.4f}")
                
        except Exception:
            print(f"    Угол {angle}°: ошибка XFOIL.")
        
        # Удаляем временный профиль
        flapped_foil_path.unlink(missing_ok=True)

    return best_angle, best_cy_max


def objective_cd_cruise(
    V_cruise: float, 
    V_stall: float, 
    AR: float, 
    mass: float,
    af_clean_path: str | Path,
    cy_max_flap: float, 
    inducted: bool
) -> float | None:
    """Считает сопротивление на крейсере."""
    density = 1.225
    g = 9.81
    
    # Площадь крыла (считается один раз, так как cy_max_flap уже известен)
    S = (2 * mass * g) / (density * V_stall**2 * cy_max_flap)
    chord = math.sqrt(S / AR)
    
    M_cruise = da.aerodynamics.mach(V_cruise, 343)
    Re_cruise = da.aerodynamics.re(V_cruise, chord)
    
    # Потребный Cy на крейсере
    cy_cruise = (2 * mass * g) / (density * V_cruise**2 * S)
    
    clean_af = da.xfoilpy.Airfoil(Path(af_clean_path).stem, str(af_clean_path))
    clean_char = da.xfoilpy.AirfoilCharacteristics(clean_af)
    
    try:
        cy_max_clean = clean_char.Cl_max(Re_cruise, M_cruise)
        if cy_max_clean is None or cy_cruise > cy_max_clean:
            return None
    except ValueError:
        return None
        
    cx_airfoil = clean_char.get_Cd_from_Cl(Re_cruise, M_cruise, cy_cruise)
    if cx_airfoil is None:
        return None 
        
    e_oswald = 0.85 
    if inducted:
        cx_induced = (cy_cruise**2) / (math.pi * AR * e_oswald)
        return cx_airfoil + cx_induced
    else:
        return cx_airfoil


def find_best_airfoil(
    V_cruise: float,
    V_stall: float,
    mass: float,
    AR: float,
    results_csv_path: str | Path = "task3_results.csv" # Путь для сохранения
):
    """Основной цикл оптимизации с сохранением результатов в DataFrame."""
    airfoils = []
    if not TASK3_AIRFOILS_PATH.exists():
        print(f"Ошибка: Папка {TASK3_AIRFOILS_PATH} не найдена!")
        return

    for file_path in TASK3_AIRFOILS_PATH.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.dat']:
            airfoil_name = file_path.stem 
            airfoils.append(da.xfoilpy.Airfoil(airfoil_name, str(file_path)))
            
    print(f"Загружено профилей: {len(airfoils)}\n")

    best_airfoil = None
    min_cd = float('inf')
    
    results_data = []

    for af in airfoils:
        print(f"Расчет профиля: {af.name}...")
        
        opt_angle, cy_max_flap = find_optimal_flap_angle(
            airfoil_path=af.path,
            V_stall=V_stall,
            AR=AR,
            mass=mass
        )
        
        if cy_max_flap <= 0:
            print(f"  Профиль {af.name} не прошел расчет. Пропуск.\n")
            continue
            
        cd_ind = objective_cd_cruise(
            V_cruise=V_cruise,
            V_stall=V_stall,
            AR=AR,
            mass=mass,
            af_clean_path=af.path,
            cy_max_flap=cy_max_flap,
            inducted=True
        )
        
        if cd_ind is not None:
            print(f"  Полный Cx: {cd_ind:.6f} (Лучший угол: {opt_angle}°)")
            
            # СОХРАНЯЕМ РЕЗУЛЬТАТ В СПИСОК
            results_data.append({
                "Airfoil": af.name,
                "Cx_total": cd_ind,
                "Cy_max": cy_max_flap,
                "Flap_Angle": opt_angle
            })
            
            if cd_ind < min_cd:
                min_cd = cd_ind
                best_airfoil = af
        else:
            print("  Сваливание на крейсере. Пропуск.")
        print() 

    print("="*50)
    if best_airfoil:
        print(f"ПОБЕДИТЕЛЬ: {best_airfoil.name}")
        print(f"Минимальный Cx: {min_cd:.6f}")
    else:
        print("Не удалось найти подходящий профиль.")
    print("="*50)
    
    # СОЗДАЕМ DATAFRAME И СОХРАНЯЕМ В CSV
    if results_data:
        df = pd.DataFrame(results_data)
        # Сортируем по возрастанию сопротивления (лучшие сверху)
        df = df.sort_values(by="Cx_total", ascending=True).reset_index(drop=True)
        
        df.to_csv(results_csv_path, index=False)
        print(f"\nРезультаты всех профилей сохранены в: {results_csv_path}")
    
    return best_airfoil

if __name__ == "__main__":
    find_best_airfoil(V_cruise=14, V_stall=9, mass=5, AR=9)
