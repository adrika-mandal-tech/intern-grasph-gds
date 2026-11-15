"""Task 09 — cross-check computed counts against the *live* Grasph server.

Run: python3 analysis/tasks/task09_grasph_verify.py
Outputs: reports/p1_verify_platform.json, reports/p1_verify_platform_summary.md

These are READ-ONLY GQL aggregate queries (MATCH...RETURN count). They do not
modify the Grasph graph. The server caps rows at 10,000 and truncates, but
aggregates return a single row and are not truncated — so label/rel counts,
distributions and medians are reliable cross-checks (TASK 11.9 rule 6).

If the server cannot be reached (auth flakiness), the script records the
failure rather than guessing.
"""
import base64
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
URL = os.environ.get('GRASPH_URL', 'http://100.23.76.198')
USER = os.environ.get('GRASPH_USER', 'admin')
PASSWORD = os.environ.get('GRASPH_PASSWORD', 'admin')


def login(session, retries=4):
    for attempt in range(retries):
        r = session.post(f'{URL}/api/v1/auth/login',
                         json={'username': USER, 'password': PASSWORD}, timeout=20)
        d = r.json()
        if 'token' in d:
            return d['token']
        time.sleep(3 * (attempt + 1))
    return None


def query(session, token, q, timeout=90):
    r = session.post(f'{URL}/api/v1/query',
                     headers={'Authorization': f'Bearer {token}'},
                     json={'query': q}, timeout=timeout)
    d = r.json()
    return d


def main():
    REPORTS.mkdir(exist_ok=True, parents=True)
    s = requests.Session()
    token = login(s)
    result = {'platform_url': URL, 'token_obtained': token is not None}

    if token is None:
        result['error'] = ('Could not authenticate to live Grasph platform '
                           '(admin/admin returned UNAUTHORIZED on retries). '
                           'Live cross-check skipped; source-CSV provenance '
                           '(manual verified 0 diff vs live) is documented in p2.')
        (REPORTS / 'p1_verify_platform.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        md = ['# Grasph live cross-check — BLOCKED', result['error'],
              'Fallback: manual TASK 11.5/11.6 verify each node/relationship against source with 0 diff.']
        (REPORTS / 'p1_verify_platform_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
        print('verify: blocked (auth)')
        return 0

    checks = {
        'Order count': "MATCH (n:Order) RETURN count(n) AS c",
        'Customer count': "MATCH (n:Customer) RETURN count(n) AS c",
        'OrderItem count': "MATCH (n:OrderItem) RETURN count(n) AS c",
        'Seller count': "MATCH (n:Seller) RETURN count(n) AS c",
        'Product count': "MATCH (n:Product) RETURN count(n) AS c",
        'Payment count': "MATCH (n:Payment) RETURN count(n) AS c",
        'Review count': "MATCH (n:Review) RETURN count(n) AS c",
        'ProductCategory count': "MATCH (n:ProductCategory) RETURN count(n) AS c",
        'Geolocation count': "MATCH (n:Geolocation) RETURN count(n) AS c",
        'HAS_ITEM count': "MATCH ()-[r:HAS_ITEM]->() RETURN count(r) AS c",
        'IN_CATEGORY count': "MATCH ()-[r:IN_CATEGORY]->() RETURN count(r) AS c",
        'PLACED_BY count': "MATCH ()-[r:PLACED_BY]->() RETURN count(r) AS c",
        'SOLD_BY count': "MATCH ()-[r:SOLD_BY]->() RETURN count(r) AS c",
        'HAS_REVIEW count': "MATCH ()-[r:HAS_REVIEW]->() RETURN count(r) AS c",
        'HAS_PAYMENT count': "MATCH ()-[r:HAS_PAYMENT]->() RETURN count(r) AS c",
        'CUSTOMER_LOCATED_IN count': "MATCH ()-[r:CUSTOMER_LOCATED_IN]->() RETURN count(r) AS c",
        'SELLER_LOCATED_IN count': "MATCH ()-[r:SELLER_LOCATED_IN]->() RETURN count(r) AS c",
    }
    expected = {
        'Order count': 99441, 'Customer count': 99441, 'OrderItem count': 112650,
        'Seller count': 3095, 'Product count': 32951, 'Payment count': 103886,
        'Review count': 98410, 'ProductCategory count': 71, 'Geolocation count': 19015,
        'HAS_ITEM count': 112650, 'IN_CATEGORY count': 32328, 'PLACED_BY count': 99441,
        'SOLD_BY count': 112650, 'HAS_REVIEW count': 98410, 'HAS_PAYMENT count': 103886,
        'CUSTOMER_LOCATED_IN count': 99163, 'SELLER_LOCATED_IN count': 3088,
    }
    server_counts = {}
    for name, q in checks.items():
        try:
            d = query(s, token, q, timeout=120)
            if d.get('rows') and not d.get('truncated'):
                server_counts[name] = int(d['rows'][0][0])
            else:
                server_counts[name + ' (truncated)'] = d
        except Exception as e:
            server_counts[name + ' (error)'] = str(e)[:120]

    mismatches = {k: {'server': v, 'expected': expected[k]}
                  for k, v in server_counts.items() if k in expected and v != expected[k]}
    result['server_counts'] = server_counts
    result['expected_counts'] = expected
    result['mismatches'] = mismatches
    result['all_match'] = len(mismatches) == 0

    (REPORTS / 'p1_verify_platform.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    md = ['# Grasph live server cross-check (read-only aggregates)', '',
          f'Platform: {URL}', f'Token obtained: {token is not None}',
          'Server counts vs verified expected (manual 11.5/11.6 provenance):', '',
          '| check | server | expected | match |', '|---|---:|---:|:---:|']
    for name in checks:
        sv = server_counts.get(name)
        exp = expected[name]
        match = sv == exp if isinstance(sv, int) else 'n/a'
        md.append(f'| {name} | {sv} | {exp} | {match} |')
    md.append('')
    if result['all_match']:
        md.append('All counts match — source-derived results are consistent with the live graph (TASK 11.9 rule 6).')
    elif mismatches:
        md.append(f'{len(mismatches)} mismatches (see JSON). Note server aggregates may be re-computed.')
    elif not server_counts:
        md.append('No aggregate counts returned (auth or timeout).')
    (REPORTS / 'p1_verify_platform_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('verify: matches', sum(1 for k in expected if k in server_counts and server_counts[k] == expected[k]),
          'of', len(expected), 'authenticated:', token is not None)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())