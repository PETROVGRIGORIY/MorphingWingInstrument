import re
from pathlib import Path

import matplotlib.pyplot as plt

from .report_base_classes import AirfoilReport
from ..objective_functions.cruise_drag_evaluation import MinCruiseDragResult


class MinCruiseDragAirfoilReport(AirfoilReport):
    """Отчёт для одного профиля при оптимизации на минимум сопротивления на крейсере.
    
    Принимает типизированный результат расчета, генерирует график профиля
    и сохраняет его вместе с таблицей расчетов в формате Markdown.
    """

    def __init__(self, result: MinCruiseDragResult):
        self._report_data = result
        self._objective_value = result.drag_X if result.drag_X is not None else float('inf')

    def to_markdown(self, path: Path) -> None:
        res = self._report_data
        af = res.airfoil
        
        slug = re.sub(r"\W+", "_", af.name).strip("_")
        img_name = f"{slug}.png"
        img_path = path.parent / img_name
        
        #Отрисовываем и сохраняем контур профиля
        ax = af.plot()
        ax.figure.savefig(img_path, dpi=120, bbox_inches="tight")
        plt.close(ax.figure)

        #Формируем Markdown
        md = f"## {af.name}\n\n"
        
        md += f"![{af.name}](report_img/{img_name})\n\n" 
        
        #Выводим результаты (обрабатываем случай, когда расчёт упал)
        if res.drag_X is None:
            md += "**Статус:** Расчет не удался, сопротивление не было расчитано\n\n"
        else:
            md += f"**Сопротивление (X):** {res.drag_X:.4f} Н\n\n"
            md += f"**Лучший угол закрылка:** {res.best_angle}° (Cy_max = {res.best_cy_max:.3f})\n\n"
        
        #Геометрия профиля
        md += f"Толщина {af.thickness:.4f} (x/c = {af.thickness_position:.3f}), "
        md += f"кривизна {af.camber:.4f} (x/c = {af.camber_position:.3f})\n\n"
        
        # 6. Таблица с перебором углов закрылка
        if not res.scan_df.empty:
            display_df = res.scan_df.round({"Cy_max": 4, "Re": 0})
            md += display_df.to_markdown(index=False) + "\n\n"
        else:
            md += "*Нет данных для таблицы (расчет не проводился)*\n\n"
        
        #Сохраняем текст
        path.write_text(md, encoding="utf-8")
