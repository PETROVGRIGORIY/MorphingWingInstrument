import os
import numpy as np
import pandas as pd

from pathlib import Path
import subprocess

from .command_files import xfoil_command_cl
from dafeaero.aerodynamics.flow import Re
from dafeaero.aerodynamics.aero_coefficients import Cl_required, Cd_induced
from dafeaero.aerodynamics.aircraft_characteristics import mean_aerodynamic_chord



class XFoilException(Exception):
    def __init__(self, text):
        self.txt = text


def run_xfoil(
    command_file: str | Path,
    xfoil_exe: str | Path,
    work_dir: str | Path | None = None
) -> Path:
    """Запускает XFOIL для выполнения файла команд commands.in
    command_file - Путь к файлу команд commands.in.
    xfoil_exe - путь к исполняемому файлу XFOIL.
    work_dir - Рабочая директория, из которой будет запущен XFOIL. 
        Если не указано, используется директория файла command_file.
        Этот параметр критически важен для корректной работы относительных 
        путей, прописанных внутри файла команд.
    """
    cmd_file = Path(command_file)
    exe = Path(xfoil_exe)

    if not exe.exists(): # Проверка существования входных файлов
        raise FileNotFoundError(f"Исполняемый файл XFOIL не найден: {exe}")
    if not cmd_file.exists():
        raise FileNotFoundError(f"Файл команд не найден: {cmd_file}")

    if work_dir is None: # Определяем рабочую директорию
        work_dir = cmd_file.parent
    else:
        work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Удаляем старую поляру, чтобы XFOIL не дописывал в неё новые данные
    polar_path = work_dir / "polar.dat"
    polar_path.unlink(missing_ok=True)
    
    # Формируем команду с перенаправлением stdin (<).
    command = f'"{exe}" < "{cmd_file.name}"'
    
    # Запускаем процесс
    result = subprocess.run(
        command,
        shell=True,
        cwd=work_dir,
        stdout=subprocess.DEVNULL, # XFOIL выводит много бесполезного текста
        stderr=subprocess.PIPE
    )

    return polar_path


def XFoil_read(file_path: str):
    '''Reads data from the last line of polar.dat file.

    :param file_path: Path of polar.dat file.
    :return: Tuple contains [alpha, cl, cd]
    :rtype: tuple[float, float, float]
    '''
    
    aero_data_file = open(file_path + 'polar.dat', 'r')
    last_line = aero_data_file.readlines()[-1].split()
    if last_line[0][:2] == '--':
        raise XFoilException(f'на одном из удлинений XFoil выдал отбивку')
    aero_data_file.close()

    os.system('del' + ' ' + file_path + 'polar.dat')
    alpha, cl, cd = float(
        last_line[0]), float(
        last_line[1]), float(
            last_line[2])
    return [alpha, cl, cd]


def K_V_solver(Sw: float, foil_name: str, v: float, ar: float, tom: float,
               xfoil_max_it: int, M: float, nu: float, ncr: int, Osvald_c: float, work_path: str, XFoil_path: str):
    '''For given parameters of airplane and flow calculates aerodynamic coefficients via XFoil

    :param Sw: wing area
    :param foil_name: Name of the file (without extension) of the main wing foil.
    :param v: Airspeed
    :param ar: Aspect ratio of the wing
    :param tom: Take-off mass
    :param xfoil_max_it: Maximum number of iterations in XFoil. Preferably between 100 and 1000.
    :param M: Mach number for XFoil calculations. For velocities less than 50 m/s can be chosen 0.
    :param nu: Dynamic viscosity.
    :param ncr: n_crit parameter in XFoil. Responsible for laminar-turbulent transition modelling. [5, 12].
    You have to calibrate this parameter for particular foil and Re. By default can be chosen 9.
    :param Osvald_c: Oswald efficiency number in induced drag coefficient formula by the lifting line theory.
    Depends from wing plan form.
    :param work_path: Working directory with foil.dat file. Also polar.dat file will be created here.
    :param XFoil_path: XFoil.exe is situated here.
    :return: [AR, V, alpha, CL, CD, CDi, K]
    :rtype: Dataframe
    '''
    polar = np.array([])
    xfoil_command_cl(Re(v, mean_aerodynamic_chord(ar, Sw), nu), Cl_required(v, Sw, tom),
                     M, ncr, xfoil_max_it, XFoil_path, work_path, foil_name)
    run_xfoil(work_path, XFoil_path)
    polar = np.append(polar, XFoil_read(work_path))

    polar = polar.reshape(polar.size // 3, 3)
    POLAR = pd.DataFrame(polar, columns=['alpha', 'CL', 'CD'])
    POLAR.insert(0, "AR", ar)
    POLAR.insert(1, "V", v)

    POLAR.insert(5, "CDi", Cd_induced(POLAR.CL, ar, osvald_coef=Osvald_c))
    POLAR.insert(6, "K", POLAR.CL / (POLAR.CD + POLAR.CDi))

    return POLAR
    # print(polar)
    # return [ar, v, polar[0][0], polar[0][1], polar[0][2], CDi(POLAR.CL, ar,
    # osvald_coef = float(settings.osvald_coef)), POLAR.CL / (POLAR.CD +
    # POLAR.CDi)]


def AR_selector(Sw: float, foil_name: str, v: float, ar_range: np.array, tom: float, xfoil_max_it: int,
                M: float, nu: float, ncr: int, Osvald_c: float, work_path: str, XFoil_path: str):
    '''Chooses the aspect ratio from given in ar_range array, which provides maximum aerodynamic efficiency
    for given airspeed.

    :param Sw: wing area
    :param foil_name: Name of the file (without extension) of the main wing foil.
    :param v: Airspeed.
    :param ar: Array with aspect ratios from witch the best would be chosen.
    :param tom: Take-off mass
    :param xfoil_max_it: Maximum number of iterations in XFoil. Preferably between 100 and 1000.
    :param M: Mach number for XFoil calculations. For velocities less than 50 m/s can be chosen 0.
    :param nu: Dynamic viscosity.
    :param ncr: n_crit parameter in XFoil. Responsible for laminar-turbulent transition modelling. [5, 12].
    You have to calibrate this parameter for particular foil and Re. By default can be chosen 9.
    :param Osvald_c: Oswald efficiency number in induced drag coefficient formula by the lifting line theory.
    Depends from wing plan form.
    :param work_path: Working directory with foil.dat file. Also polar.dat file will be created here.
    :param XFoil_path: XFoil.exe is situated here.
    :return: aspect ratio
    :rtype: float
    '''
    df = pd.DataFrame()
    for ar in ar_range:
        try:
            p = K_V_solver(
                Sw,
                foil_name,
                v,
                ar,
                tom,
                xfoil_max_it,
                M,
                nu,
                ncr,
                Osvald_c,
                work_path,
                XFoil_path)
            # print(p)
            df = pd.concat([df, p], ignore_index=True, sort=False)
        except XFoilException as e:
            print(e)

    return df.iloc[df.K.argmax()].AR


def XFoil_command_TE_gap(work_path, foil_name, gap, chord, blending_dist=0.4):
    '''Forms the text command file for XFoil.
    '''
    command_file = open(work_path + 'commands.in', 'w')
    command_file.write('load ' + work_path + foil_name + '.dat' + '\n'
                       + foil_name + '\n\
    gdes\n\
    tgap ' + str(gap / chord) + ' ' + str(blending_dist) + '\n\
    exec\n\
    \n\
    psav ' + work_path + foil_name + f'g_{gap / chord}' + '.dat' + '\n\
    quit\n')
    command_file.close()
    return 0
