from pathlib import Path

from .base_classes import Airfoil, AnglesOfAttackSequence
from .command_files import xfoil_command_aseq
from .run_xfoil import run_xfoil
from .parse_polar import parse_xfoil_polar
from .plots import ComparisonMode, PlotData, plots_to_comparison


XFOIL_EXE_PATH = Path(__file__).parent / "xfoil_software" / "xfoil.exe"
SOLVER_WORKIDR_PATH = Path(__file__).parent / "solver_workdir"


class AirfoilComparator:
    """Этот класс позволяет работать с профилями и сравнивать их."""
    _airfoils: list[Airfoil]

    def __init__(self):
        self._airfoils = []

    def _airfoil_search(self, name: str):
        """Поиск профиля по имени. Возвращает объект Airfoil.
        Если профиль не найден, бросается ValueError"""
        for af in self._airfoils:
            if af.name == name:
                return af
        raise ValueError("Профиль {name} не был добавлен.")

    def add_airfoil(self, airfoil: Airfoil):
        self._airfoils.append(airfoil)

    def cl_alpha_plot(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence,
        airfoilnames: tuple[str],
        mode_of_comparison: ComparisonMode,
        plot_name: str = "",
        path_of_polar_plor_image: str = ""
    ) -> None:
        """ """
        airfoils_data = []

        if isinstance(airfoilnames, str):
            airfoilnames = (airfoilnames,)

        for name in airfoilnames:
            try:
                airfoil = self._airfoil_search(name)
            except ValueError:
                print(f"Профиль {name} не был найден, над ним не будет расчёта")
                continue
            command_file_path = xfoil_command_aseq(
                Re, M, aoas, ncr, max_it, airfoil.path, SOLVER_WORKIDR_PATH
            )
            polar_file_path = run_xfoil(
                command_file_path, XFOIL_EXE_PATH, SOLVER_WORKIDR_PATH
            )
            polar_df, _ = parse_xfoil_polar(polar_file_path)

            # Сортируем по углу атаки и убираем дубликаты
            polar_df = (
                polar_df
                .drop_duplicates(subset='alpha')   # убираем дубли по alpha
                .sort_values('alpha')              # сортируем по возрастанию
                .reset_index(drop=True)            # сбрасываем старый индекс
            )

            angles = polar_df['alpha'].to_numpy()
            cl = polar_df['CL'].to_numpy()
            airfoils_data.append(
                PlotData(name, angles, cl)
            )
        plots_to_comparison(
            airfoils_data, mode_of_comparison,
            "угол атаки", "Cy", plot_name, path_of_polar_plor_image)

    def cd_alpha_plot(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence,
        airfoilnames: tuple[str],
        mode_of_comparison: ComparisonMode,
        plot_name: str = "",
        path_of_polar_plor_image: str = ""
    ) -> None:
        """ """
        airfoils_data = []

        if isinstance(airfoilnames, str):
            airfoilnames = (airfoilnames,)

        for name in airfoilnames:
            try:
                airfoil = self._airfoil_search(name)
            except ValueError:
                print(f"Профиль {name} не был найден, над ним не будет расчёта")
                continue
            command_file_path = xfoil_command_aseq(
                Re, M, aoas, ncr, max_it, airfoil.path, SOLVER_WORKIDR_PATH
            )
            polar_file_path = run_xfoil(
                command_file_path, XFOIL_EXE_PATH, SOLVER_WORKIDR_PATH
            )
            polar_df, _ = parse_xfoil_polar(polar_file_path)

            # Сортируем по углу атаки и убираем дубликаты
            polar_df = (
                polar_df
                .drop_duplicates(subset='alpha')   # убираем дубли по alpha
                .sort_values('alpha')              # сортируем по возрастанию
                .reset_index(drop=True)            # сбрасываем старый индекс
            )

            angles = polar_df['alpha'].to_numpy()
            cl = polar_df['CD'].to_numpy()
            airfoils_data.append(
                PlotData(name, angles, cl)
            )
        plots_to_comparison(
            airfoils_data, mode_of_comparison,
            "угол атаки", "Cx", plot_name, path_of_polar_plor_image)
