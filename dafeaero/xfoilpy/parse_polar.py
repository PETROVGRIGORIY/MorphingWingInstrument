import pandas as pd

import re


def parse_xfoil_polar(filepath):
    """Читает файл поляры XFOIL и возвращает (DataFrame, metadata)."""
    metadata = {}
    rows = []
    header_done = False

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue

            # Метаданные
            if 'Version' in s:
                metadata['version'] = s.split('Version')[-1].strip()
            elif 'Calculated polar for:' in s:
                metadata['airfoil'] = s.split(':')[-1].strip()
            elif s.startswith('xtrf'):
                m = re.findall(r'([\d.]+)', s)
                if len(m) >= 2:
                    metadata['xtrf_top'] = float(m[0])
                    metadata['xtrf_bot'] = float(m[1])
            elif s.startswith('Mach'):
                m = re.search(r'Mach\s*=\s*([\d.]+)\s+Re\s*=\s*([\d.]+)\s*e\s*(\d+)\s+Ncrit\s*=\s*([\d.]+)', s)
                if m:
                    metadata['Mach']  = float(m.group(1))
                    metadata['Re']    = float(m.group(2)) * 10**int(m.group(3))
                    metadata['Ncrit'] = float(m.group(4))

            # Шапка таблицы
            elif s.startswith('alpha'):
                header_done = True
                continue

            # Данные
            elif header_done and re.match(r'^[\s\-\d]', s):
                parts = s.split()
                if len(parts) == 7:
                    try:
                        rows.append([float(x) for x in parts])
                    except ValueError:
                        pass

    cols = ['alpha', 'CL', 'CD', 'CDp', 'CM', 'Top_Xtr', 'Bot_Xtr']
    polar_df = pd.DataFrame(rows, columns=cols)

    return polar_df, metadata
