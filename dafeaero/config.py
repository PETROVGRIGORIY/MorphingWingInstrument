from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

XFOIL_EXE_PATH = BASE_DIR / "xfoilpy" / "xfoil_software" / "xfoil.exe"

#Время в с, после которого прекращаются попытки завершить расчёт, возбуждается ValueError
XFOIL_TIMEOUT = 60