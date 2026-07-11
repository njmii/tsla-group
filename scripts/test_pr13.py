#!/usr/bin/env python3
"""
Regression tests for PR13 formula (A11668).

Expected values match the dashboard's 1dp output (contribution × 12 ACE for all certs).

Usage:
    python3 scripts/test_pr13.py
"""

import json
import datetime
import os
import sys

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'data', 'pr-data.json')


def get_ace(c):
    """Mirror JS getACE: use stored ace, fall back to contribution × 12."""
    return c.get('ace') or round((c.get('contribution') or 0) * 12, 2)


def pr13_window(proj_year, proj_month_0):
    """Return (window_start, window_end) date objects for the PR13 cohort."""
    import calendar
    base = proj_year * 12 + proj_month_0
    we_m = base - 13
    ws_m = base - 24
    we_y, we_mo = divmod(we_m, 12)
    ws_y, ws_mo = divmod(ws_m, 12)
    window_end   = datetime.date(we_y, we_mo + 1,
                                  calendar.monthrange(we_y, we_mo + 1)[1])
    window_start = datetime.date(ws_y, ws_mo + 1, 1)
    return window_start, window_end


def calc_pr13(clients, proj_year, proj_month_0):
    """
    Compute PR13% (1dp) for the given client list and projection month.
    proj_month_0 is 0-indexed (January=0).
    Returns float or None if no eligible certs.
    """
    # last day of projection month
    import calendar
    last_day = calendar.monthrange(proj_year, proj_month_0 + 1)[1]
    proj_last = datetime.date(proj_year, proj_month_0 + 1, last_day)

    ws, we = pr13_window(proj_year, proj_month_0)
    elig_ace = 0.0
    coll_ace = 0.0

    for c in clients:
        if not c.get('issueDate'):
            continue
        issued = datetime.date.fromisoformat(c['issueDate'])
        if issued < ws or issued > we:
            continue
        if c.get('status') == 'Freelook Cancellation':
            continue

        # point-in-time status
        eff = c.get('status', '')
        if eff in ('Lapsed', 'Contract Surrendered') and c.get('statusUpdatedDate'):
            upd = datetime.date.fromisoformat(c['statusUpdatedDate'])
            if upd > proj_last:
                eff = 'In Force'

        ace = get_ace(c)
        elig_ace += ace
        if eff in ('In Force', 'Contract Surrendered'):
            coll_ace += ace

    if elig_ace == 0:
        return None
    return round(coll_ace / elig_ace * 1000) / 10


def main():
    with open(DATA_PATH) as f:
        data = json.load(f)

    ag = next((a for a in data['agents'] if a['code'] == 'A11668'), None)
    if ag is None:
        print("FAIL: agent A11668 not found in data")
        sys.exit(1)

    clients = ag['clients']

    # (year, month_0_indexed, label, expected_pct)
    cases = [
        (2026, 5, 'June 2026',  93.2),
        (2026, 4, 'May 2026',   95.6),
        (2026, 3, 'April 2026', 95.2),
        (2026, 2, 'March 2026', 95.5),
    ]

    all_pass = True
    for yr, mo, label, expected in cases:
        got = calc_pr13(clients, yr, mo)
        status = 'PASS' if got == expected else 'FAIL'
        if status == 'FAIL':
            all_pass = False
        print(f"{status}  {label}: expected {expected}%  got {got}%")

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
