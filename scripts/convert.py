#!/usr/bin/env python3
"""
Convert FWD Certificate Listing xlsx -> data/pr-data.json

Usage:
    python3 scripts/convert.py <path-to-xlsx> [output-json]

If output-json is omitted, writes to data/pr-data.json.

Requirements: Python 3.8+, no extra packages (uses only stdlib).
Uses direct XML/zip parsing to avoid openpyxl stylesheet compat bugs.
"""

import sys
import json
import zipfile
import xml.etree.ElementTree as ET
import re
import os
from datetime import date, datetime
from collections import defaultdict

DOWNLINES = {
    'A11668': ['A13290', 'A14252', 'A12322'],
}

# Shared strings XML namespace
NS = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def parse_xlsx(path):
    with zipfile.ZipFile(path) as zf:
        # Load shared strings
        shared = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            tree = ET.parse(zf.open('xl/sharedStrings.xml'))
            for si in tree.getroot():
                t = ''.join(n.text or '' for n in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))
                shared.append(t)

        # Load the first sheet
        sheet_path = 'xl/worksheets/sheet1.xml'
        tree = ET.parse(zf.open(sheet_path))
        root = tree.getroot()

    rows = []
    for row in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
        cells = {}
        for cell in row:
            ref = cell.get('r', '')
            col = re.sub(r'\d', '', ref)
            t = cell.get('t', '')
            v_el = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            val = v_el.text if v_el is not None else None
            if t == 's' and val is not None:
                val = shared[int(val)]
            cells[col] = val
        rows.append(cells)
    return rows


def col_letter(n):
    """0-indexed column number to Excel letter (A, B, ..., Z, AA, ...)"""
    result = ''
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def excel_date(val):
    """Convert Excel serial date or ISO string to YYYY-MM-DD string."""
    if val is None:
        return None
    if isinstance(val, str) and re.match(r'\d{4}-\d{2}-\d{2}', val):
        return val[:10]
    try:
        serial = float(val)
        # Excel epoch is 1900-01-01 (with the Lotus 1-2-3 leap-year bug: day 60 = Feb 29 1900)
        if serial >= 60:
            serial -= 1
        d = date(1899, 12, 31).toordinal() + int(serial)
        return date.fromordinal(d).isoformat()
    except (ValueError, TypeError):
        return str(val) if val else None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    xlsx_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'pr-data.json'
    )

    print(f"Reading {xlsx_path}...")
    rows = parse_xlsx(xlsx_path)

    # Find header row (contains "Certificate No.")
    header_row_idx = None
    header_map = {}
    for i, row in enumerate(rows):
        for col, val in row.items():
            if val and 'Certificate No' in str(val):
                header_row_idx = i
                break
        if header_row_idx is not None:
            break

    if header_row_idx is None:
        print("ERROR: Could not find header row with 'Certificate No.'")
        sys.exit(1)

    header = rows[header_row_idx]
    print(f"Header row at index {header_row_idx}: {header}")

    # Map column letters to field names
    field_map = {
        'Selling Agent Code':    'agentCode',
        'Selling Agent':         'agentName',
        'Life Assured':          'name',
        'Certificate No.':       'certNo',
        'Certificate Status':    'status',
        'Pay Mode':              'payMode',
        'Plan':                  'plan',
        'Issue Date':            'issueDate',
        'Due Date':              'dueDate',
        'Contribution Amount':   'contribution',
        'Payment Method Code':   'payMethod',
        'Status Updated Date':   'statusUpdatedDate',
        'ACE':                   'ace',
    }

    col_to_field = {}
    for col, val in header.items():
        if val and str(val).strip() in field_map:
            col_to_field[col] = field_map[str(val).strip()]

    print(f"Column mapping: {col_to_field}")

    # Parse data rows
    clients_by_agent = defaultdict(list)
    agent_names = {}
    data_rows = rows[header_row_idx + 1:]

    for row in data_rows:
        if not row:
            continue
        rec = {}
        for col, field in col_to_field.items():
            rec[field] = row.get(col)

        if not rec.get('certNo'):
            continue

        # Parse dates
        for date_field in ('issueDate', 'dueDate', 'statusUpdatedDate'):
            rec[date_field] = excel_date(rec.get(date_field))

        # Parse numbers
        for num_field in ('contribution', 'ace'):
            v = rec.get(num_field)
            try:
                rec[num_field] = round(float(v), 2) if v is not None else None
            except (ValueError, TypeError):
                rec[num_field] = None

        agent_code = rec.pop('agentCode', None)
        agent_name = rec.pop('agentName', None)
        if not agent_code:
            continue

        if agent_name:
            agent_names[agent_code] = agent_name
        clients_by_agent[agent_code].append(rec)

    # Build agents list
    agents = []
    for code, clients in sorted(clients_by_agent.items()):
        agent = {
            'code': code,
            'name': agent_names.get(code, code),
            'clients': clients,
        }
        if code in DOWNLINES:
            agent['downlines'] = DOWNLINES[code]
        agents.append(agent)

    out = {
        'updated': date.today().isoformat(),
        'agents': agents,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)

    total = sum(len(a['clients']) for a in agents)
    print(f"Wrote {out_path}: {len(agents)} agents, {total} clients")


if __name__ == '__main__':
    main()
