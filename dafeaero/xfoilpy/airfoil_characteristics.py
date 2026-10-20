from pathlib import Path

import pandas as pd
import numpy as np

from .base_classes import Airfoil, AnglesOfAttackSequence
from .command_files import xfoil_command_aseq
from .run_xfoil import run_xfoil
from .parse_polar import parse_xfoil_polar

XFOIL_EXE_PATH = Path(__file__).parent / "xfoil_software" / "xfoil.exe"
SOLVER_WORKIDR_PATH = Path(__file__).parent / "solver_workdir"


class AirfoilCharacteristics():
    _airfoil: Airfoil

    def __init__(self, airfoil: Airfoil):
        self._airfoil = airfoil

    def compute_airfoil_polar(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence,
    ) -> pd.DataFrame:
        """Считает поляру aэродинамического профиля.
        Возвращает DataFrame - конвертированный результат расчёта xfoil"""

        command_file_path = xfoil_command_aseq(
            Re, M, aoas, ncr, max_it, self._airfoil.path, SOLVER_WORKIDR_PATH
        )
        polar_file_path = run_xfoil(
            command_file_path, XFOIL_EXE_PATH, SOLVER_WORKIDR_PATH
        )
        polar_df, _ = parse_xfoil_polar(polar_file_path)

        return (
            polar_df
            .drop_duplicates(subset='alpha')
            .sort_values('alpha')
            .reset_index(drop=True)
        )

    def Cl_max(self, Re: float, M: float,):
        """Вычисляет максимальный Cy для профиля,
        Re - число Рейнольдса,
        M - число Маха.
        Расчёт в xfoil при ncr = 9, max_iter = 250,
        углы атаки в градусах: от -5 до 20 с шагом 1
        """
        aseq = AnglesOfAttackSequence(0, 5, 1)
        polar_df = self.compute_airfoil_polar(Re, M, 9, 250, aseq)

        if not isinstance(polar_df, pd.DataFrame) or polar_df.empty:
            raise ValueError("Не удалось корректно вычислить поляру профиля")

        return max(polar_df['CL'])

    def get_Cd_from_Cl(
        self, 
        Re: float, 
        M: float, 
        cl_target: float,
        ncr: int = 9,
        max_it: int = 250
    ) -> tuple[float, float] | None:
        """Рассчитывает Cx под заданный Cy. Если заданный Cy не достигается ни на одном
        из углов атаки от 0 до 20 градусов, бросается ValueError."""

        aseq = AnglesOfAttackSequence(0, 5, 1)
        polar_df = self.compute_airfoil_polar(Re, M, ncr, max_it, aseq)
        
        if not isinstance(polar_df, pd.DataFrame) or polar_df.empty:
            raise ValueError("Не удалось корректно вычислить поляру профиля")

        df = polar_df[['CL', 'CD']]

        #Для numpy интерполяции, нам необходимо монотонное возрастание элементов 
        #Cl и Cd по углу атаки, поэтому выкидывем точки после срыва потока.
        max_cl_idx = df['CL'].idxmax()
        df_pre_stall = df.loc[:max_cl_idx]

        cy_values = df_pre_stall['CL'].to_numpy()
        cx_values = df_pre_stall['CD'].to_numpy()

        #Проверяем, попадает ли целевой Cy в рабочий диапазон
        if cl_target < cy_values.min() or cl_target > cy_values.max():
            return None

        cx_interpolated = np.interp(cl_target, cy_values, cx_values)
        
        return cx_interpolated
