import os
from pathlib import Path

from .base_classes import AnglesOfAttackSequence

def xfoil_command_cl(
        RE: float,
        CL: float,
        M: float,
        ncr: int,
        xfoil_max_it: int,
        foil_path: str | Path,
        output_dir: str | Path
) -> Path:
    """ Формирует текстовый файл команд для запуска XFOIL в режиме
    расчёта угла атаки, при котором достигается заданный CL.
    Создаёт файл commands.in в рабочей директорииy.
    RE - Число Рейнольдса.
    CL - Целевой коэффициент подъёмной силы.
        При этом CL XFOIL найдёт соответствующий угол атаки.
    M - Число Маха.
    ncr - Критический параметр N (Ncrit) метода e^N для моделирования
        перехода ламинарного → турбулентного пограничного слоя.
    xfoil_max_it - Максимальное число итераций расчётника
    XFoil_path - Путь к исполняемому файлу XFOIL
    foil_path - Путь к файлу координат профиля
    output_dir - Путь к директории, куда будут сохранены файл команд.
    Если директории не существует, она будет создана автоматически. """

    foil = Path(foil_path)
    out_dir = Path(output_dir)
    
    out_dir.mkdir(parents=True, exist_ok=True)
    foil_name = foil.stem
    
    # Вычисляем относительный путь от output_dir до файла профиля
    try:
        rel_foil_path = os.path.relpath(foil, out_dir)
    except ValueError:
        # На Windows упадет, если файлы на разных дисках. 
        # В этом случае fallback на абсолютный путь.
        rel_foil_path = str(foil)

    polar_filename = "polar.dat"

    commands = (
        f"load {rel_foil_path}\n"
        f"{foil_name}\n"
        f"plop\n"
        f"g f\n"
        f"\n"
        f"oper\n"
        f"visc {RE}\n"
        f"M {M}\n"
        f"type 1\n"
        f"vpar\n"
        f"n {ncr}\n"
        f"\n"
        f"iter {xfoil_max_it}\n"
        f"pacc\n"
        f"{polar_filename}\n"
        f"\n"
        f"cl {CL}\n"
        f"\n"
        f"\n"
        f"quit\n"
    )

    command_file_path = out_dir / "commands.in"

    with open(command_file_path, "w") as f:
        f.write(commands)

    return command_file_path


def xfoil_command_aseq(
        RE: float,
        M: float,
        aoas: AnglesOfAttackSequence,
        ncr: int,
        xfoil_max_it: int,
        foil_path: str | Path,
        output_dir: str | Path
) -> Path:
    """ Формирует текстовый файл команд для запуска XFOIL в режиме
    вычисления при углах атаки от alpha_first до alpha_last с шагом step.
    Создаёт файл commands.in в рабочей директории.
    RE - Число Рейнольдса.
    aoas - последовательность углов атаки
    M - Число Маха.
    ncr - Критический параметр N (Ncrit) метода e^N для моделирования
        перехода ламинарного → турбулентного пограничного слоя.
    xfoil_max_it - Максимальное число итераций расчётника
    foil_path - Путь к файлу координат профиля
    output_dir - Путь к директории, куда будут сохранены файл команд.
    Если директории не существует, она будет создана автоматически. """

    foil = Path(foil_path)
    out_dir = Path(output_dir)
    
    out_dir.mkdir(parents=True, exist_ok=True)
    foil_name = foil.stem
    
    # Вычисляем относительный путь от output_dir до файла профиля
    try:
        rel_foil_path = os.path.relpath(foil, out_dir)
    except ValueError:
        # На Windows упадет, если файлы на разных дисках. 
        # В этом случае fallback на абсолютный путь.
        rel_foil_path = str(foil)

    polar_filename = "polar.dat"

    base_commands = (
        f"load {rel_foil_path}\n"
        f"{foil_name}\n"
        f"plop\n"
        f"g f\n"
        f"\n"
        f"oper\n"
        f"visc {RE}\n"
        f"M {M}\n"
        f"type 1\n"
        f"vpar\n"
        f"n {ncr}\n"
        f"\n"
        f"iter {xfoil_max_it}\n"
        f"pacc\n"
        f"{polar_filename}\n"
        f"\n"
    )

    if  aoas.alpha_first >= 0:
        commands = base_commands + (
            f"aseq {aoas.alpha_first} {aoas.alpha_last} {aoas.step}\n"
            f"\n"
            f"\n"
            f"quit\n"
        )
    else:
        commands = base_commands + (
            f"aseq 0 {aoas.alpha_last} {aoas.step}\n"
            f"init\n"
            f"aseq 0 {aoas.alpha_first} {aoas.step}\n"
            f"\n"
            f"\n"
            f"quit\n"
        )

    command_file_path = out_dir / "commands.in"

    with open(command_file_path, "w") as f:
        f.write(commands)

    return command_file_path
