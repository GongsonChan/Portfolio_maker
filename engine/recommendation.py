"""
현재 포트폴리오 추천
- 백테스트(스코어링/테스트 분리)와 달리, 가장 최근 N개월 데이터 전체를 스코어링에 사용
- 미래 성과는 알 수 없으므로 종목 비중만 제공
"""
import numpy as np
import pandas as pd
from engine.scoring import compute_features, score_assets
from engine.selection import select_assets


def get_current_recommendation(prices: pd.DataFrame, macro: pd.DataFrame,
                                 assets: pd.DataFrame, fundamentals: pd.DataFrame,
                                 corr_matrix: pd.DataFrame, params: dict) -> dict:
    scoring_months  = params.get("scoring_months", params.get("backtest_months", 24))
    backtest_months = scoring_months  # score_assets 호환용
    end = prices.index.max()
    start = max(prices.index.min(), end - pd.DateOffset(months=scoring_months))

    # 최근 N개월 전체로 스코어링 (분리 없음)
    rec_prices_window = prices.loc[start:end]
    if len(rec_prices_window) < 20:
        return {"status": "insufficient_data"}

    # compute_features는 내부에서 scoring window를 자동 계산하므로
    # 여기서는 백테스트 기간을 절반으로 줘서 최근 데이터 전체를 scoring에 사용
    # → backtest_months를 크게 설정하면 test_start가 더 앞으로 가서 최근 데이터를 scoring에 포함
    # 더 직접적인 방법: compute_features에 명시적 기간 파라미터 전달
    # 현재 구조에서 가장 간단한 방법: backtest_months*2를 넣어 scoring window = 최근 N개월

    # 직접 피처 계산 (최근 N개월 전체 사용)
    p = rec_prices_window.pct_change(fill_method=None)
    rf = macro.loc[start:end, "fed_funds_rate"].mean() / 100 if "fed_funds_rate" in macro.columns else 0.0

    rows = []
    for t in p.columns:
        r = p[t].dropna()
        if len(r) < 20:
            continue
        ann_ret = float((1 + r).prod() - 1)
        ann_vol = r.std() * np.sqrt(252)
        sharpe  = (ann_ret - rf) / ann_vol if ann_vol > 0 else np.nan
        cum     = (1 + r).cumprod()
        roll_max = cum.cummax()
        mdd     = ((cum - roll_max) / roll_max).min()

        mkt = assets.loc[assets["ticker"] == t, "market"].values
        mkt = mkt[0] if len(mkt) else "US"
        bench_col = "SPY" if mkt == "US" else "069500"
        if bench_col in p.columns:
            rb = p[bench_col].dropna()
            common = r.index.intersection(rb.index)
            if len(common) > 10:
                cov_ab = np.cov(r.loc[common], rb.loc[common])[0, 1]
                var_b  = rb.loc[common].var()
                beta   = cov_ab / var_b if var_b > 0 else np.nan
                bench_ann = float((1 + rb).prod() - 1)
                alpha = ann_ret - beta * bench_ann if not np.isnan(beta) else np.nan
            else:
                beta, alpha = np.nan, np.nan
        else:
            beta, alpha = np.nan, np.nan

        fund = fundamentals[fundamentals["ticker"] == t].sort_values("date")
        last = fund.iloc[-1] if len(fund) else pd.Series(dtype=float)

        rows.append({
            "ticker": t,
            "annualized_return": ann_ret,
            "annualized_vol":    ann_vol,
            "sharpe_ratio":      sharpe,
            "max_drawdown":      mdd,
            "beta":              beta,
            "alpha":             alpha,
            "pe_ratio":          last.get("pe_ratio", np.nan),
            "pb_ratio":          last.get("pb_ratio", np.nan),
            "roe":               last.get("roe", np.nan),
            "dividend_yield":    last.get("dividend_yield", np.nan),
            "debt_to_equity":    last.get("debt_to_equity", np.nan),
            "revenue_growth":    last.get("revenue_growth", np.nan),
            "market_cap":        last.get("market_cap", np.nan),
            "avg_volume":        r.abs().rolling(60).mean().iloc[-1] if len(r) >= 60 else np.nan,
        })

    if not rows:
        return {"status": "no_data"}

    feat = pd.DataFrame(rows).set_index("ticker")
    scores, universe, status = score_assets(feat, assets, params, prices, backtest_months)

    if status != "ok":
        return {"status": status}

    selected, weights = select_assets(scores, corr_matrix, assets, params)
    if not selected:
        return {"status": "selection_empty"}

    return {
        "status":   "ok",
        "selected": selected,
        "weights":  weights,
        "as_of":    end.strftime("%Y-%m-%d"),
        "period":   f"최근 {scoring_months}개월 ({start.strftime('%Y-%m')} ~ {end.strftime('%Y-%m')})",
    }
