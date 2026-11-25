from .polar import Polar
from .airfoil import Airfoil
from ..xfoilpy.base_classes import AnglesOfAttackSequence
from ..service.plots import PlotData, ComparisonMode, plots_to_comparison


class AirfoilComparator:
    """Этот класс позволяет сделать прикидочное сравнение небольшого количества профилей"""
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

    def _compute_polars(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence | tuple[float, float, float],
        airfoilnames: str | tuple[str, ...],
    ) -> list[tuple[str, Polar]]:
        """Вспомогательный метод: считает (или достает из кэша) поляры для списка профилей.
        Re - Число Рейнольдса.
        M - Число Маха.
        ncr - Критический параметр N (Ncrit) метода e^N для моделирования
            ламинарно-турбулентного перехода пограничного слоя.
        max_it - Максимальное число итераций расчётника.
        aoas - Последовательность углов атаки.
        airfoilnames - Имя профиля или кортеж имён профилей или "" 
            (если передана пустая строка, берутся все добавленные в компаратор профили).
        """
        if not airfoilnames:
            # Если пустая строка, берем все добавленные профили
            airfoilnames = tuple(af.name for af in self._airfoils)
        elif isinstance(airfoilnames, str):
            airfoilnames = (airfoilnames,)
            
        polars = []
        for name in airfoilnames:
            airfoil = self._airfoil_search(name)
            polar = airfoil.polar(Re=Re, M=M, aoas=aoas, ncr=ncr, max_it=max_it)
            polars.append((name, polar))
            
        return polars

    def cl_alpha_plot(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence | tuple[float, float, float],
        airfoilnames: str | tuple[str, ...],
        separate_plots: bool = False,
        plot_name: str = "",
        path_of_polar_plor_image: str = ""
    ) -> None:
        """Строит график зависимости коэффициента подъемной силы (CL) от угла атаки.
        Re - Число Рейнольдса.
        M - Число Маха.
        ncr - Критический параметр N (Ncrit) метода e^N для моделирования
            ламинарно-турбулентного перехода пограничного слоя.
        max_it - Максимальное число итераций расчётника.
        aoas - Последовательность углов атаки.
        airfoilnames - Имя профиля или кортеж имён профилей или "" 
            (если передана пустая строка, берутся все добавленные в компаратор профили).
        separate_plots - Если True, каждый профиль рисуется на отдельном графике, 
            иначе все на одном.
        plot_name - Заголовок графика.
        path_of_polar_plor_image - Путь для сохранения изображения графика.
        """        
        polars = self._compute_polars(Re, M, ncr, max_it, aoas, airfoilnames)
        
        airfoils_data = [
            PlotData(name, polar.alpha, polar.cl) 
            for name, polar in polars
        ]
        
        mode = ComparisonMode.SEPARATE if separate_plots else ComparisonMode.COMBINED
        
        plots_to_comparison(
            airfoils_data, mode,
            "угол атаки", "Cy", plot_name, path_of_polar_plor_image
        )

    def cd_alpha_plot(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence | tuple[float, float, float],
        airfoilnames: str | tuple[str, ...],
        separate_plots: bool = False,
        plot_name: str = "",
        path_of_polar_plor_image: str = ""
    ) -> None:
        """Строит график зависимости коэффициента сопротивления (CD) от угла атаки.
        Re - Число Рейнольдса.
        M - Число Маха.
        ncr - Критический параметр N (Ncrit) метода e^N для моделирования
            ламинарно-турбулентного перехода пограничного слоя.
        max_it - Максимальное число итераций расчётника.
        aoas - Последовательность углов атаки.
        airfoilnames - Имя профиля или кортеж имён профилей или "" 
            (если передана пустая строка, берутся все добавленные в компаратор профили).
        separate_plots - Если True, каждый профиль рисуется на отдельном графике, 
            иначе все на одном.
        plot_name - Заголовок графика.
        path_of_polar_plor_image - Путь для сохранения изображения графика.
        """
        polars = self._compute_polars(Re, M, ncr, max_it, aoas, airfoilnames)
        
        airfoils_data = [
            PlotData(name, polar.alpha, polar.cd) 
            for name, polar in polars
        ]
        
        mode = ComparisonMode.SEPARATE if separate_plots else ComparisonMode.COMBINED
        
        plots_to_comparison(
            airfoils_data, mode,
            "угол атаки", "Cx", plot_name, path_of_polar_plor_image
        )

    def quality_alpha_plot(
        self,
        Re: float,
        M: float,
        ncr: int,
        max_it: int,
        aoas: AnglesOfAttackSequence | tuple[float, float, float],
        airfoilnames: str | tuple[str, ...],
        separate_plots: bool = False,
        plot_name: str = "",
        path_of_polar_plor_image: str = ""
    ) -> None:
        """Строит график аэродинамического качества (CL/CD) от угла атаки.
        Re - Число Рейнольдса.
        M - Число Маха.
        ncr - Критический параметр N (Ncrit) метода e^N для моделирования
            ламинарно-турбулентного перехода пограничного слоя.
        max_it - Максимальное число итераций расчётника.
        aoas - Последовательность углов атаки.
        airfoilnames - Имя профиля или кортеж имён профилей или "" 
            (если передана пустая строка, берутся все добавленные в компаратор профили).
        separate_plots - Если True, каждый профиль рисуется на отдельном графике, 
            иначе все на одном.
        plot_name - Заголовок графика.
        path_of_polar_plor_image - Путь для сохранения изображения графика.
        """
        polars = self._compute_polars(Re, M, ncr, max_it, aoas, airfoilnames)
        
        airfoils_data = [
            PlotData(name, polar.alpha, polar.cl / polar.cd) 
            for name, polar in polars
        ]
        
        mode = ComparisonMode.SEPARATE if separate_plots else ComparisonMode.COMBINED
        
        plots_to_comparison(
            airfoils_data, mode,
            "угол атаки", "Cy / Cx", plot_name, path_of_polar_plor_image
        )
