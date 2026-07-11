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


X13_PLANS = {'FWD Life First', 'FWD Protect First', 'FWD Income First'}
# Submitted before FWD's ×13 effective date — confirmed ×12 via FWD portal
FORCE_X12 = {'AN443318', 'AN457372'}

def get_ace(c):
    """Mirror JS getACE: ×13 for qualifying plan/date/amount, else stored ace or ×12."""
    iss = c.get('issueDate') or ''
    if (c.get('certNo') not in FORCE_X12 and c.get('plan') in X13_PLANS
            and '2024-07-01' <= iss <= '2024-11-30'
            and (c.get('contribution') or 0) >= 200):
        return round((c.get('contribution') or 0) * 13, 2)
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


def months_diff(d1_str, d2_str):
    if not d1_str or not d2_str:
        return 0
    d1 = datetime.date.fromisoformat(d1_str)
    d2 = datetime.date.fromisoformat(d2_str)
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def calc_pr13(clients, proj_year, proj_month_0):
    """
    Compute PR13% (2dp) for the given client list and projection month.
    proj_month_0 is 0-indexed (January=0).
    Returns float or None if no eligible certs.
    """
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

        eff = c.get('status', '')
        upd_str = c.get('statusUpdatedDate', '')

        if eff == 'Contract Surrendered' and upd_str:
            if datetime.date.fromisoformat(upd_str) > proj_last:
                eff = 'In Force'
        elif eff == 'Lapsed' and upd_str:
            if (datetime.date.fromisoformat(upd_str) > proj_last and
                    months_diff(c.get('issueDate'), c.get('dueDate')) >= 13):
                eff = 'In Force'

        ace = get_ace(c)
        elig_ace += ace
        if eff == 'In Force':
            coll_ace += ace
        elif eff == 'Contract Surrendered':
            if months_diff(c.get('issueDate'), upd_str) >= 13:
                coll_ace += ace

    if elig_ace == 0:
        return None
    return round(coll_ace / elig_ace * 10000) / 100


def main():
    with open(DATA_PATH) as f:
        data = json.load(f)

    all_pass = True

    # A11668 Najmi Fikri — verified against FWD portal
    ag = next((a for a in data['agents'] if a['code'] == 'A11668'), None)
    if ag is None:
        print("FAIL: agent A11668 not found in data")
        sys.exit(1)

    print("A11668 Najmi Fikri:")
    for yr, mo, label, expected in [
        (2026, 5, 'June 2026',  93.43),
        (2026, 4, 'May 2026',   95.74),
        (2026, 3, 'April 2026', 95.33),
        (2026, 2, 'March 2026', 95.68),
    ]:
        got = calc_pr13(ag['clients'], yr, mo)
        status = 'PASS' if got == expected else 'FAIL'
        if status == 'FAIL':
            all_pass = False
        print(f"  {status}  {label}: expected {expected}%  got {got}%")

    # A14252 Roza — verified against FWD portal
    ag2 = next((a for a in data['agents'] if a['code'] == 'A14252'), None)
    if ag2 is None:
        print("FAIL: agent A14252 not found in data")
        sys.exit(1)

    print("A14252 Roza:")
    for yr, mo, label, expected in [
        (2026, 4, 'May 2026',   77.22),
        (2026, 3, 'April 2026', 77.53),
        (2026, 2, 'March 2026', 85.22),
    ]:
        got = calc_pr13(ag2['clients'], yr, mo)
        status = 'PASS' if got == expected else 'FAIL'
        if status == 'FAIL':
            all_pass = False
        print(f"  {status}  {label}: expected {expected}%  got {got}%")

    # A13290 Naqiyuddin — verified against FWD portal
    ag3 = next((a for a in data['agents'] if a['code'] == 'A13290'), None)
    if ag3 is None:
        print("FAIL: agent A13290 not found in data")
        sys.exit(1)

    print("A13290 Naqiyuddin:")
    for yr, mo, label, expected in [
        (2026, 4, 'May 2026', 63.79),
    ]:
        got = calc_pr13(ag3['clients'], yr, mo)
        status = 'PASS' if got == expected else 'FAIL'
        if status == 'FAIL':
            all_pass = False
        print(f"  {status}  {label}: expected {expected}%  got {got}%")

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
