"""Подбор профиля и угла закрылка по сопротивлению на крейсере.
Во время расчёта пишет отчёт Markdown; в конце строит 4 графика зависимости Cx от геометрии."""
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # без окон: графики только в файлы
import matplotlib.pyplot as plt
import pandas as pd

import dafeaero as da

AIRFOILS_PATH = Path("task4_foils")
REPORT_DIR = Path("task4_report")
FLAP_ANGLES = range(0, 36, 5)
HINGE_X = 0.75
OSWALD = 0.85


def _slug(name: str) -> str:
    return re.sub(r"\W+", "_", name).strip("_")


def _md_table(df: pd.DataFrame, floatfmt: str = ".5g") -> str:
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for _, row in df.iterrows():
        cells = [f"{v:{floatfmt}}" if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n\n"


def stall_cl(af: da.Airfoil, V_stall: float, AR: float, mass: float) -> tuple[float, float]:
    """Cy_max на скорости сваливания; Re уточняется по хорде, которая зависит от Cy_max."""
    M = da.aerodynamics.mach(V_stall, da.a0)
    cy = 1.5                                      # начальное приближение для закрылка
    for _ in range(4):
        S = 2 * mass * da.g / (da.rho0 * V_stall**2 * cy)
        Re = da.aerodynamics.re(V_stall, math.sqrt(S / AR))
        cy_new = af.polar(Re, M).cl_max
        converged = abs(cy_new - cy) < 1e-3
        cy = cy_new
        if converged:
            break
    return cy, Re


def scan_flap(af: da.Airfoil, V_stall: float, AR: float, mass: float) -> list[tuple]:
    """Cy_max для каждого угла закрылка: список (угол, Cy_max, Re). Неудачные углы пропускаются."""
    rows = []
    for angle in FLAP_ANGLES:
        try:
            flapped = af.with_flap(angle, HINGE_X) if angle else af
            cy, Re = stall_cl(flapped, V_stall, AR, mass)
        except Exception as exc:
            print(f"    Угол {angle}°: ошибка ({exc})")
            continue
        print(f"    Угол {angle}°: Cy_max = {cy:.4f} (Re = {Re:.0f})")
        rows.append((angle, cy, Re))
    return rows


def cruise_cd(af: da.Airfoil, V_cruise: float, V_stall: float, AR: float,
              mass: float, cy_max_flap: float) -> float | None:
    """Полный Cx на крейсере (профильный + индуктивный) или None, если профиль сваливается."""
    S = 2 * mass * da.g / (da.rho0 * V_stall**2 * cy_max_flap)
    chord = math.sqrt(S / AR)
    cy = 2 * mass * da.g / (da.rho0 * V_cruise**2 * S)
    try:
        polar = af.polar(da.aerodynamics.re(V_cruise, chord),
                         da.aerodynamics.mach(V_cruise, da.a0))
        if cy > polar.cl_max:
            return None
        cd = polar.cd_at_cl(cy)
    except ValueError:
        return None
    return cd + cy**2 / (math.pi * AR * OSWALD)


def _load_airfoils() -> list[da.Airfoil]:
    if not AIRFOILS_PATH.exists():
        raise FileNotFoundError(f"Папка {AIRFOILS_PATH} не найдена")
    airfoils = []
    for path in sorted(AIRFOILS_PATH.iterdir()):
        if path.suffix in (".txt", ".dat"):
            try:
                airfoils.append(da.Airfoil.from_file(path))
            except Exception as exc:
                print(f"Не удалось прочитать {path.name}: {exc}")
    return airfoils


def _save_airfoil_plot(af: da.Airfoil, path: Path) -> None:
    ax = af.plot()
    ax.figure.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(ax.figure)


def _save_summary_plot(df: pd.DataFrame, path: Path) -> None:
    panels = [("thickness", "Максимальная толщина, t/c"),
              ("thickness_pos", "Положение максимальной толщины, x/c"),
              ("camber", "Максимальная кривизна, f/c"),
              ("camber_pos", "Положение максимальной кривизны, x/c")]
    best = df["Cx_total"].idxmin()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (col, label) in zip(axes.flat, panels):
        ax.scatter(df[col], df["Cx_total"], s=30)
        ax.scatter(df.loc[best, col], df.loc[best, "Cx_total"], s=90, c="red",
                   label=f"лучший: {df.loc[best, 'Airfoil']}")
        ax.set_xlabel(label)
        ax.set_ylabel("Cx на крейсере")
        ax.grid(True, ls=":")
    axes.flat[0].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def find_best_airfoil(V_cruise: float, V_stall: float, mass: float, AR: float,
                      report_dir: str | Path = REPORT_DIR) -> da.Airfoil | None:
    report_dir = Path(report_dir)
    img_dir = report_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    airfoils = _load_airfoils()
    print(f"Загружено профилей: {len(airfoils)}\n")

    results, best_airfoil = [], None
    # buffering=1: отчёт пишется построчно, его можно открывать и обновлять во время расчёта
    with open(report_dir / "report.md", "w", encoding="utf-8", buffering=1) as md:
        md.write("# Подбор профиля\n\n"
                 f"V крейсерская = {V_cruise} м/с, V сваливания = {V_stall} м/с, "
                 f"масса = {mass} кг, удлинение = {AR}, шарнир закрылка x/c = {HINGE_X}\n\n")

        for af in airfoils:
            print(f"Расчёт профиля: {af.name}")
            slug = _slug(af.name)
            _save_airfoil_plot(af, img_dir / f"{slug}.png")
            md.write(f"## {af.name}\n\n![{af.name}](img/{slug}.png)\n\n"
                     f"Толщина {af.thickness:.4f} (x/c = {af.thickness_position:.3f}), "
                     f"кривизна {af.camber:.4f} (x/c = {af.camber_position:.3f})\n\n")

            try:
                scan = scan_flap(af, V_stall, AR, mass)
                if not scan:
                    md.write("Расчёт не удался ни при одном угле закрылка. Профиль пропущен.\n\n")
                    continue
                md.write(_md_table(pd.DataFrame(scan, columns=["Угол закрылка, °", "Cy_max", "Re"])))

                angle, cy_max, _ = max(scan, key=lambda r: r[1])
                cx = cruise_cd(af, V_cruise, V_stall, AR, mass, cy_max)
            except Exception as exc:
                print(f"  Ошибка расчёта: {exc}\n")
                md.write(f"Ошибка расчёта: {exc}. Профиль пропущен.\n\n")
                continue

            if cx is None:
                print("  Сваливание на крейсере. Пропуск.\n")
                md.write(f"Лучший угол закрылка {angle}° (Cy_max = {cy_max:.3f}), "
                         "но на крейсере профиль сваливается. Пропущен.\n\n")
                continue

            print(f"  Полный Cx: {cx:.6f} (лучший угол: {angle}°)\n")
            md.write(f"**Лучший угол закрылка: {angle}°, Cy_max = {cy_max:.3f}. "
                     f"Cx на крейсере = {cx:.6f}**\n\n")
            results.append({
                "Airfoil": af.name, "thickness": af.thickness,
                "thickness_pos": af.thickness_position, "camber": af.camber,
                "camber_pos": af.camber_position, "Flap_Angle": angle,
                "Cy_max": cy_max, "Cx_total": cx,
            })
            if best_airfoil is None or cx < min(r["Cx_total"] for r in results[:-1] or [{"Cx_total": math.inf}]):
                best_airfoil = af

        md.write("## Итоги\n\n")
        if not results:
            md.write("Не удалось найти подходящий профиль.\n")
            return None

        df = pd.DataFrame(results).sort_values("Cx_total").reset_index(drop=True)
        df.to_csv(report_dir / "results.csv", index=False)
        _save_summary_plot(df, img_dir / "summary.png")
        md.write(f"Лучший профиль: **{df.loc[0, 'Airfoil']}** "
                 f"(Cx = {df.loc[0, 'Cx_total']:.6f}, закрылок {df.loc[0, 'Flap_Angle']}°)\n\n"
                 "![Зависимость Cx от геометрии](img/summary.png)\n\n"
                 "У симметричных профилей кривизна и её положение равны нулю, "
                 "поэтому их точки лежат на оси.\n\n")
        md.write(_md_table(df))

    return best_airfoil


if __name__ == "__main__":
    find_best_airfoil(V_cruise=14, V_stall=9, mass=5, AR=9)
