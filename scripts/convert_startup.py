"""
FWD Start-Up Elite Scheme — Excel → JSON converter
Usage: python3 scripts/convert_startup.py <path-to-xlsx>
Output: data/startup-data.json

Run this monthly when you receive the new validation Excel.
"""

import sys, json, math, warnings, os
from datetime import date

warnings.filterwarnings('ignore')

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas not installed. Run: pip install pandas openpyxl")

def norm(v):
    return str(v).replace('\xa0', ' ').split() and ' '.join(str(v).replace('\xa0', ' ').split()) or ''

def safe_float(v):
    try:
        f = float(v)
        return 0.0 if math.isnan(f) else f
    except:
        return 0.0

def safe_str(v):
    s = str(v).strip() if v is not None else ''
    return '' if s in ('nan', 'None', 'NaT') else s

def convert(xlsx_path, out_path):
    xl = pd.ExcelFile(xlsx_path)
    if 'Summary' not in xl.sheet_names:
        sys.exit("ERROR: 'Summary' sheet not found in " + xlsx_path)

    df = xl.parse('Summary', header=None)

    # Find header row by locating "Agent Code"
    hdr_row = None
    for i, row in df.iterrows():
        for v in row.values:
            if str(v).strip() == 'Agent Code':
                hdr_row = i
                break
        if hdr_row is not None:
            break
    if hdr_row is None:
        sys.exit("ERROR: Header row with 'Agent Code' not found")

    # Extract report title from pre-header rows
    title = 'Start-Up Elite Scheme'
    for i in range(hdr_row):
        for v in df.iloc[i].values:
            s = safe_str(v).lower()
            if 'start-up' in s or 'startup' in s or ('elite' in s and 'scheme' in s):
                title = safe_str(v)
                break

    # Build column map from normalised header names (collapses any multi-spaces)
    hdr = df.iloc[hdr_row]
    col_map = {}
    for col_idx, val in enumerate(hdr.values):
        k = ' '.join(str(val).replace('\xa0', ' ').split())
        if k:
            col_map[k] = col_idx

    def _norm_key(field):
        return ' '.join(str(field).replace('\xa0', ' ').split())

    def get(row, field, default=''):
        idx = col_map.get(_norm_key(field))
        if idx is None:
            return default
        v = row.iloc[idx] if hasattr(row, 'iloc') else row[idx]
        return safe_str(v)

    def getf(row, field):
        return safe_float(get(row, field, 0))

    data_rows = df.iloc[hdr_row + 1:].reset_index(drop=True)

    agent_map = {}
    for _, row in data_rows.iterrows():
        code = get(row, 'Agent Code')
        if not code or code in ('Total', 'Grand Total', 'Agent Code'):
            continue
        name = get(row, 'Full Name')
        if not name:
            continue

        if code not in agent_map:
            agent_map[code] = {
                'code':    code,
                'name':    name,
                'agency':  get(row, 'Agency Name'),
                'scheme':  get(row, 'Scheme'),
                'status':  get(row, 'Status'),
                'ytdACE':         0.0,
                'ytdTargetACE':   0.0,
                'ytdCases':       0.0,
                'ytdTargetCases': 0.0,
                'ytdNOC':         0.0,
                'ytdPayout':      0.0,
                'totalPayout':    0.0,
                'ce':   None,
                'pr13': None,
                'training': '',
                'remark':   '',
                'months': [],
            }

        a = agent_map[code]
        # Overwrite YTD fields — later rows (more recent months) win
        a['ytdACE']         = getf(row, 'YTD  ACE')
        a['ytdTargetACE']   = getf(row, 'YTD Target ACE')
        a['ytdCases']       = getf(row, 'YTD  Cases')
        a['ytdTargetCases'] = getf(row, 'YTD Target Cases')
        a['ytdNOC']         = getf(row, 'YTD NOC')
        a['ytdPayout']      = getf(row, 'YTD Total Payout')
        a['totalPayout']    = getf(row, 'Total Payout')
        a['training']       = get(row, 'Training Completion')
        a['remark']         = get(row, 'Remark')

        ce_raw = get(row, 'CE %')
        if ce_raw:
            a['ce'] = safe_float(ce_raw)
        pr_raw = get(row, 'PR13')
        if pr_raw:
            a['pr13'] = safe_float(pr_raw)

        a['months'].append({
            'month':          int(getf(row, 'Month')) if getf(row, 'Month') else 0,
            'evalMonth':      get(row, 'Evaluation Month'),
            'mtdACE':         getf(row, 'MTD ACE'),
            'mtdTarget':      getf(row, 'MTD Target ACE'),
            'mtdCases':       getf(row, 'MTD Cases'),
            'mtdTargetCases': getf(row, 'MTD Target Cases'),
            'mtdNOC':         getf(row, 'MTD NOC'),
            'mtdResult':      get(row, 'MTD Result'),
            'mtdPayout':      getf(row, 'Monthly Payout'),
            'catchResult':    get(row, 'Catch-up Result'),
            'catchPayout':    getf(row, 'Catch-up Payout'),
        })

    agents = [a for a in agent_map.values()
              if a['name'] and (a['ytdTargetACE'] > 0 or a['ytdACE'] > 0)]

    output = {
        'title':   title,
        'updated': date.today().isoformat(),
        'agents':  agents,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    print(f"✓ {len(agents)} agents written to {out_path}")
    print(f"  Title: {title}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/convert_startup.py <path-to-xlsx>")
        print("Example: python3 scripts/convert_startup.py 'Startup Jun26.xlsx'")
        sys.exit(1)
    xlsx = sys.argv[1]
    out  = os.path.join(os.path.dirname(__file__), '..', 'data', 'startup-data.json')
    convert(xlsx, out)
