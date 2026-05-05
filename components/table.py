import streamlit as st
import pandas as pd
import numpy as np


def _fmt_pct(v, decimals=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v*100:.{decimals}f}%"


def _fmt_num(v, decimals=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v:.{decimals}f}"


def render_table(metrics: dict, backtest_months: int = 12, scoring_months: int = 24):
    user = metrics.get("user", {})
    presets = metrics.get("presets", {})
    benchmarks = metrics.get("benchmarks", {})

    rows = {
        f"수익률 — 테스트 ({backtest_months}개월, 아웃오브샘플)": ("returns",          _fmt_pct),
        f"수익률 — 스코어링 (이전 {scoring_months}개월, 인샘플)": ("returns_scoring", _fmt_pct),
        "연환산 수익률 (테스트 기간)":                             ("returns_annualized", _fmt_pct),
        "변동성 (연환산)":                                        ("volatility",       _fmt_pct),
        "샤프 비율":         ("sharpe_ratio",    _fmt_num),
        "알파":              ("alpha",           _fmt_pct),
        "최대 낙폭 (MDD)":   ("max_drawdown",    _fmt_pct),
        "배당수익률":        ("dividend_yield",  _fmt_pct),
        "Portfolio Score":   ("portfolio_score", lambda v: _fmt_num(v) if v != "N/A" else "N/A"),
    }

    label_map = {"aggressive": "공격형", "balanced": "균형형", "conservative": "안정형"}
    bench_keys = list(benchmarks.keys())

    data = {"지표": [], "내 포트폴리오": []}
    for pn in ["aggressive", "balanced", "conservative"]:
        data[label_map[pn]] = []
    for bk in bench_keys:
        data[bk] = []

    for label, (key, fmt) in rows.items():
        data["지표"].append(label)
        data["내 포트폴리오"].append(fmt(user.get(key, np.nan)))
        for pn in ["aggressive", "balanced", "conservative"]:
            pm = presets.get(pn, {})
            data[label_map[pn]].append(fmt(pm.get(key, np.nan)))
        for bk in bench_keys:
            bm = benchmarks.get(bk, {})
            if key in ("dividend_yield", "portfolio_score"):
                data[bk].append("N/A")
            else:
                data[bk].append(fmt(bm.get(key, np.nan)))

    df = pd.DataFrame(data).set_index("지표")
    st.dataframe(df, use_container_width=True)
