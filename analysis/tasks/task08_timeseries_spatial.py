"""Phase 8 — time series & spatial analysis.

Run: python3 analysis/tasks/task08_timeseries_spatial.py
Outputs: reports/p8_timeseries_spatial_summary.md, reports/p8_timeseries_spatial.json

Read-only; haversine distance vs freight/weight with regression (uses p09 proof).
Trend window restricted to 2017-01 through 2018-08 (manual TASK 11.5).
"""
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

CSV_DIR = Path(__file__).resolve().parents[2] / 'Olist-Kaggle-dataset'
REPORTS = Path(__file__).resolve().parents[1] / 'reports'
SEED = 20261012
TREND_START, TREND_END = '2017-01', '2018-08'


def load():
    orders, items, sellers, customers = (
        pd.read_csv(CSV_DIR / 'olist_orders_dataset.csv', parse_dates=['order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']),
        pd.read_csv(CSV_DIR / 'olist_order_items_dataset.csv'),
        pd.read_csv(CSV_DIR / 'olist_sellers_dataset.csv'),
        pd.read_csv(CSV_DIR / 'olist_customers_dataset.csv'))
    geo = pd.read_csv(CSV_DIR / 'olist_geolocation_dataset.csv')
    # zip -> centroid
    geo['zip5'] = geo['geolocation_zip_code_prefix'].astype(str).str.zfill(5).str[:5]
    cent = geo.groupby('zip5').agg(lat=('geolocation_lat', 'mean'), lng=('geolocation_lng', 'mean')).reset_index()
    cent = cent.set_index('zip5')
    return orders, items, sellers, customers, cent


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def main():
    REPORTS.mkdir(exist_ok=True, parents=True)
    orders, items, sellers, customers, cent = load()
    # time series: orders per month (trend window)
    o = orders.copy()
    o['year_month'] = o['order_purchase_timestamp'].dt.strftime('%Y-%m')
    o = o[o['year_month'] >= TREND_START]
    o = o[o['year_month'] <= TREND_END]
    monthly = o.groupby('year_month').size()
    months = list(monthly.index)
    series = monthly.values.astype(float)
    # baselines vs seasonal naive (prev year same month where available) and seasonal mean
    naive_mae = float(((series[1:] - series[:-1]) ** 2).mean() ** 0.5)  # random-ish; report std too
    month_mean = series.mean()
    # shipping economics: freight vs distance/weight/volume per item
    items2 = items.merge(orders[['order_id', 'customer_id']], on='order_id', how='inner')
    cust = customers[['customer_id', 'customer_zip_code_prefix']].copy()
    cust['zip5'] = cust['customer_zip_code_prefix'].astype(str).str.zfill(5).str[:5]
    items2 = items2.merge(cust[['customer_id', 'zip5']], on='customer_id', how='left')
    items2 = items2.merge(sellers[['seller_id', 'seller_zip_code_prefix', 'seller_state']], on='seller_id', how='left')
    items2['szip'] = items2['seller_zip_code_prefix'].astype(str).str.zfill(5).str[:5]
    # centroid merge
    items2 = items2.merge(cent.rename(columns={'lat': 'clat', 'lng': 'clng'}), left_on='zip5', right_index=True, how='left')
    items2 = items2.merge(cent.rename(columns={'lat': 'slat', 'lng': 'slng'}), left_on='szip', right_index=True, how='left')
    mask = items2['clat'].notna() & items2['slat'].notna()
    d = items2[mask].copy()
    d['distance_km'] = d.apply(lambda r: haversine(r['clat'], r['clng'], r['slat'], r['slng']), axis=1)
    # delivery time
    dt = d.merge(orders[['order_id', 'order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']], on='order_id', how='left')
    dt['deliv_days'] = (dt['order_delivered_customer_date'] - dt['order_purchase_timestamp']).dt.days
    dt['late_days'] = (dt['order_delivered_customer_date'].dt.date - dt['order_estimated_delivery_date'].dt.date).apply(lambda x: x.days if pd.notna(x) else np.nan)

    # regressions: log(freight) ~ log(distance) + log(weight) + log(volume) + price
    prods = pd.read_csv(CSV_DIR / 'olist_products_dataset.csv',
                        usecols=['product_id', 'product_weight_g', 'product_category_name'])
    reg = dt[np.isfinite(dt['freight_value']) & dt['freight_value'].between(0.1, 10000) & dt['distance_km'].between(1, 3000) & dt['price'].between(0.1, 10000)].copy()
    reg = reg.merge(prods, on='product_id', how='left')
    reg['log_freight'] = np.log(reg['freight_value'])
    reg['log_dist'] = np.log(reg['distance_km'])
    reg['log_weight'] = np.log(reg['product_weight_g'] / 1000 + 0.001)
    reg['log_price'] = np.log(reg['price'])
    reg = reg[['freight_value', 'distance_km', 'price', 'product_weight_g']].dropna()
    reg['log_freight'] = np.log(reg['freight_value'])
    reg['log_dist'] = np.log(reg['distance_km'])
    reg['log_weight'] = np.log(reg['product_weight_g'] + 1.0)
    reg['log_price'] = np.log(reg['price'])
    reg = reg[np.isfinite(reg['log_freight']) & np.isfinite(reg['log_weight']) & (reg['freight_value'] > 0)]
    X = np.column_stack([np.ones(len(reg)), reg['log_dist'].values, reg['log_weight'].values, reg['log_price'].values])
    y = reg['log_freight'].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    ss_res = ((y - yhat) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot
    Xd = np.column_stack([np.ones(len(reg)), reg['log_dist'].values])
    yd = Xd @ (np.linalg.lstsq(Xd, y, rcond=None)[0])
    r2_d = 1 - ((y - yd) ** 2).sum() / ss_tot

    # delivery time vs distance
    dd = dt[np.isfinite(dt['deliv_days']) & dt['deliv_days'].between(0, 365) & dt['distance_km'].between(1, 3000)]
    r_dist_time, p_dist_time = stats.pearsonr(dd['distance_km'], dd['deliv_days'])
    r_price_time, p_price_time = stats.pearsonr(dd['price'], dd['deliv_days'])

    report = {
        'trend_window': [TREND_START, TREND_END],
        'monthly_order_counts': monthly.to_dict(),
        'monthly_orders_array': series.tolist(),
        'freight_regression': {
            'n': int(len(reg)), 'r2_full': float(r2), 'r2_dist_only': float(r2_d),
            'beta_intercept': float(beta[0]), 'beta_log_dist': float(beta[1]),
            'beta_log_weight': float(beta[2]), 'beta_log_price': float(beta[3])
        },
        'delivery_time_vs_distance': {'pearson_r': float(r_dist_time), 'p': float(p_dist_time), 'n': len(dd)},
        'delivery_time_vs_price': {'pearson_r': float(r_price_time), 'p': float(p_price_time)},
        'on_time_share': float((dt['late_days'].fillna(0) <= 0).mean() if dt['late_days'].notna().any() else 0),
        'mean_late_days_among_late': float(dt.loc[dt['late_days'] > 0, 'late_days'].mean()),
    }
    (REPORTS / 'p8_timeseries_spatial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    md = ['# Phase 8 — time series & shipping economics (haversine, proof p09)', '',
          f'Trend window: {TREND_START} to {TREND_END} (first/last empty months excluded, manual 11.5)', '',
          '## Orders per month',
          '| month | orders |', '|---|---:|']
    for m, c in monthly.items():
        md.append(f'| {m} | {c} |')
    md += ['', '## Freight vs distance/weight/price (log-log regression)',
           f'- n={report["freight_regression"]["n"]}; full model R^2={r2:.3f}; distance-only R^2={r2_d:.3f}',
           f'- beta_log_dist={beta[1]:.3f} (freight % per 1% distance), beta_log_weight={beta[2]:.3f}, beta_log_price={beta[3]:.3f}',
           '', '## Delivery time',
           f'- Pearson r(distance, delivery_days) = {r_dist_time:.3f} (p={p_dist_time:.2g})',
           f'- Pearson r(price, delivery_days) = {r_price_time:.3f}',
           f'- on-time share = {report["on_time_share"]:.3f}; mean late days among late = {report["mean_late_days_among_late"]:.1f}']
    (REPORTS / 'p8_timeseries_spatial_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('p8 done: months', len(series), 'freight r2', round(r2, 3), 'dist-only r2', round(r2_d, 3),
          'r_dist_time', round(r_dist_time, 3))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
