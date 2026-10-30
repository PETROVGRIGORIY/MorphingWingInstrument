import os
import uuid
from pathlib import Path

from ..xfoilpy.run_xfoil import run_xfoil

XFOIL_EXE_PATH = Path(__file__).parent.parent / "xfoilpy" / "xfoil_software" / "xfoil.exe"
AIRFOILS_WORKIDR_PATH = Path(__file__).parent / "airfoils_workdir"


def add_flap_to_airfoil(
    flap_angle: int | float,
    hinge_position: float,
    airfoil_path: str | Path,
    modified_airfoil_path: str | Path
):
    """Функция принимает профиль, добавляет закрылок по параметрам,
    сохраняет изменённый профиль.
    Важно! координата y считается xfoil по умолчанию.
    flap_angle - угол отклонения закрылка
    hinge_position - позиция шарнира в долях от длины хорды
    airfoil_path - путь к профилю
    modified_airfoil_path - путь для сохранения изменённого профиля"""

    foil = Path(airfoil_path).resolve()
    mod_foil = Path(modified_airfoil_path).resolve()
    
    AIRFOILS_WORKIDR_PATH.mkdir(parents=True, exist_ok=True)

    # Так как запуск происходит в SOLVER_WORKIDR_PATH, пути считаем от нее
    try:
        rel_foil_path = os.path.relpath(foil, AIRFOILS_WORKIDR_PATH)
    except ValueError:
        rel_foil_path = str(foil)

    commands = (
        f"load {rel_foil_path}\n"
        f"{foil.stem}\n"
        f"gdes\n"
        f"flap\n"
        f"{hinge_position}\n"
        f"999\n"
        f"1\n"
        f"{flap_angle}\n"
        f"exec\n"
        f"\n"
        f"psav {mod_foil.name}\n"
        f"quit\n"
    )

    # Создаем уникальное имя для командного файла
    unique_id = uuid.uuid4().hex[:8]  # Берем первые 8 символов UUID
    cmd_filename = f"commands_flap_{unique_id}.in"
    cmd_file = AIRFOILS_WORKIDR_PATH / cmd_filename
    
    cmd_file.write_text(commands)

    # Запускаем в рабочей папке
    run_xfoil(cmd_file, XFOIL_EXE_PATH, AIRFOILS_WORKIDR_PATH)
    
    # Сразу удаляем командный файл после расчета
    cmd_file.unlink(missing_ok=True)

    saved_foil = AIRFOILS_WORKIDR_PATH / mod_foil.name
    if not saved_foil.exists():
        raise RuntimeError(f"XFOIL не сохранил профиль: {saved_foil}")
        
    mod_foil.parent.mkdir(parents=True, exist_ok=True)
    saved_foil.replace(mod_foil)

    return mod_foil
