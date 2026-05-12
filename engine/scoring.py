import numpy as np
import pandas as pd


def _normalize(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def _normalize_risk(series: pd.Series) -> pd.Series:
    return 1 - _normalize(series)


def compute_features(prices: pd.DataFrame, macro: pd.DataFrame,
                     assets: pd.DataFrame, fundamentals: pd.DataFrame,
                     backtest_months: int, params: dict) -> pd.DataFrame:
    # 스코어링 기간: 테스트 기간 이전 구간 (룩어헤드 바이어스 방지)
    scoring_months = params.get("scoring_months", backtest_months)
    end   = prices.index.max()
    test_start    = end - pd.DateOffset(months=backtest_months)
    scoring_end   = test_start
    scoring_start = max(prices.index.min(),
                        scoring_end - pd.DateOffset(months=scoring_months))
    p = prices.loc[scoring_start:scoring_end]
    returns = p.pct_change(fill_method=None)  # 종목별로 개별 처리

    rf = macro.loc[scoring_start:scoring_end, "fed_funds_rate"].mean() / 100 if "fed_funds_rate" in macro.columns else 0.0

    tickers = list(returns.columns)
    rows = []
    for t in tickers:
        r = returns[t].dropna()
        if len(r) < 20:
            continue
        ann_ret  = float((1 + r).prod() - 1)  # 백테스트 기간 누적 수익률
        ann_vol  = r.std() * np.sqrt(252)
        sharpe   = (ann_ret - rf) / ann_vol if ann_vol > 0 else np.nan
        cum      = (1 + r).cumprod()
        roll_max = cum.cummax()
        mdd      = ((cum - roll_max) / roll_max).min()

        mkt = assets.loc[assets["ticker"] == t, "market"].values
        mkt = mkt[0] if len(mkt) else "US"
        bench_col = "SPY" if mkt == "US" else "069500"
        if bench_col in returns.columns:
            rb = returns[bench_col].dropna()
            common = r.index.intersection(rb.index)
            if len(common) > 10:
                cov_ab = np.cov(r.loc[common], rb.loc[common])[0, 1]
                var_b  = rb.loc[common].var()
                beta   = cov_ab / var_b if var_b > 0 else np.nan
                bench_ann = (1 + rb.mean()) ** 252 - 1
                alpha = ann_ret - beta * bench_ann if not np.isnan(beta) else np.nan
            else:
                beta, alpha = np.nan, np.nan
        else:
            beta, alpha = np.nan, np.nan

        fund = fundamentals[(fundamentals["ticker"] == t) & (fundamentals["date"] <= scoring_end)].sort_values("date")
        last = fund.iloc[-1] if len(fund) else pd.Series(dtype=float)

        rows.append({
            "ticker":             t,
            "annualized_return":  ann_ret,
            "annualized_vol":     ann_vol,
            "sharpe_ratio":       sharpe,
            "max_drawdown":       mdd,
            "beta":               beta,
            "alpha":              alpha,
            "pe_ratio":           last.get("pe_ratio", np.nan),
            "pb_ratio":           last.get("pb_ratio", np.nan),
            "roe":                last.get("roe", np.nan),
            "dividend_yield":     last.get("dividend_yield", np.nan),
            "debt_to_equity":     last.get("debt_to_equity", np.nan),
            "revenue_growth":     last.get("revenue_growth", np.nan),
            "market_cap":         last.get("market_cap", np.nan),
        })

    if not rows:
        raise ValueError(
            f"스코어링 기간({scoring_start.date()} ~ {scoring_end.date()})에 "
            f"유효한 종목이 없습니다. 백테스트 기간을 줄여보세요."
        )
    df = pd.DataFrame(rows).set_index("ticker")
    df["avg_volume"] = returns.apply(lambda r: r.dropna().abs().rolling(60).mean().iloc[-1] if len(r.dropna()) > 0 else np.nan).reindex(df.index)
    return df


def compute_rsi(prices: pd.DataFrame, scoring_months: int, window: int = 14) -> pd.Series:
    end   = prices.index.max()
    start = end - pd.DateOffset(months=scoring_months)
    p = prices.loc[start:end]
    delta = p.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs   = gain / loss.replace(0, np.nan)
    rsi  = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def compute_momentum(prices: pd.DataFrame, scoring_months: int, window: int) -> pd.Series:
    end   = prices.index.max()
    start = end - pd.DateOffset(months=scoring_months)
    p = prices.loc[start:end]
    if len(p) < window:
        return pd.Series(np.nan, index=p.columns)
    return p.iloc[-1] / p.iloc[-window] - 1


def compute_var_cvar(prices: pd.DataFrame, scoring_months: int,
                     level: float = 0.05) -> tuple[pd.Series, pd.Series]:
    end   = prices.index.max()
    start = end - pd.DateOffset(months=scoring_months)
    r = prices.loc[start:end].pct_change().dropna()
    var   = r.quantile(level)
    cvar  = r.apply(lambda col: col[col <= col.quantile(level)].mean())
    return var, cvar


def score_assets(feat: pd.DataFrame, assets: pd.DataFrame,
                 params: dict, prices: pd.DataFrame,
                 backtest_months: int) -> tuple[pd.Series, list, str]:
    meta = assets.set_index("ticker")

    universe = feat.index[
        feat.index.isin(meta.index) &
        (meta.reindex(feat.index)["asset_type"] == "stock") &
        (meta.reindex(feat.index)["is_active"] == True) &
        (
            (params["allow_us"] & (meta.reindex(feat.index)["market"] == "US")) |
            (params["allow_kr"] & (meta.reindex(feat.index)["market"] == "KR"))
        )
    ].tolist()

    f = feat.loc[universe].copy()
    m = meta.reindex(universe)

    # Step 1: Fundamental filters (NaN passes)
    if params.get("use_pe_filter"):
        mask = f["pe_ratio"].isna() | (f["pe_ratio"] <= params["pe_max"])
        f = f[mask]; m = m[mask]

    if params.get("use_pb_filter"):
        mask = f["pb_ratio"].isna() | (f["pb_ratio"] <= params["pb_max"])
        f = f[mask]; m = m[mask]

    if params.get("use_roe_filter"):
        mask = f["roe"].isna() | (f["roe"] >= params["roe_min"])
        f = f[mask]; m = m[mask]

    if params.get("use_div_filter"):
        mask = f["dividend_yield"].isna() | (f["dividend_yield"] >= params["div_min"])
        f = f[mask]; m = m[mask]

    if params.get("use_de_filter"):
        mask = f["debt_to_equity"].isna() | (f["debt_to_equity"] <= params["de_max"])
        f = f[mask]; m = m[mask]

    if params.get("use_rev_growth_filter"):
        mask = f["revenue_growth"].isna() | (f["revenue_growth"] >= params["rev_growth_min"])
        f = f[mask]; m = m[mask]

    if params.get("use_mcap_filter"):
        pct = params["mcap_percentile_min"]
        for mkt in ["US", "KR"]:
            idx = m[m["market"] == mkt].index
            if len(idx) == 0:
                continue
            thresh = np.nanpercentile(f.loc[idx, "market_cap"].dropna(), pct)
            keep = f.loc[idx, "market_cap"].isna() | (f.loc[idx, "market_cap"] >= thresh)
            drop = idx[~keep]
            f = f.drop(drop); m = m.drop(drop)

    if params.get("use_volume_filter"):
        pct = params["volume_percentile_min"]
        for mkt in ["US", "KR"]:
            idx = m[m["market"] == mkt].index
            if len(idx) == 0:
                continue
            thresh = np.nanpercentile(f.loc[idx, "avg_volume"].dropna(), pct)
            keep = f.loc[idx, "avg_volume"].isna() | (f.loc[idx, "avg_volume"] >= thresh)
            drop = idx[~keep]
            f = f.drop(drop); m = m.drop(drop)

    if len(f) == 0:
        return pd.Series(dtype=float), [], "filter_empty"

    # Step 1.5: Technical indicators
    rsi_vals = pd.Series(np.nan, index=f.index)
    mom_vals = pd.Series(np.nan, index=f.index)
    var_vals  = pd.Series(np.nan, index=f.index)
    cvar_vals = pd.Series(np.nan, index=f.index)

    tickers_avail = [t for t in f.index if t in prices.columns]

    # 기술적 지표 — 스코어링 기간(테스트 기간 이전) 기준으로 계산 (룩어헤드 바이어스 방지)
    sm = params.get("scoring_months", backtest_months)
    end_p = prices.index.max()
    scoring_end_p   = end_p - pd.DateOffset(months=backtest_months)
    scoring_start_p = max(prices.index.min(),
                          scoring_end_p - pd.DateOffset(months=sm))
    scoring_months  = max(1, int((scoring_end_p - scoring_start_p).days / 30))
    # 테스트 기간 데이터를 제외하고 스코어링 기간까지만 잘라서 전달
    scoring_prices  = prices[tickers_avail].loc[:scoring_end_p]
    rsi_all = compute_rsi(scoring_prices, scoring_months) if params.get("use_rsi_filter") else None
    var_all, cvar_all = compute_var_cvar(scoring_prices, scoring_months) if params.get("use_var_cvar_filter") else (None, None)
    mom_window = min(params.get("momentum_window", 126), scoring_months * 21)
    mom_all = compute_momentum(scoring_prices, scoring_months, mom_window) if params.get("use_momentum") else None

    if rsi_all is not None:
        rsi_vals.update(rsi_all)
        mask = rsi_vals.isna() | (rsi_vals <= params["rsi_upper_bound"])
        f = f[mask]; m = m[mask]; rsi_vals = rsi_vals[mask]

    if params.get("use_beta_filter"):
        mask = f["beta"].isna() | ((f["beta"] >= params["beta_min"]) & (f["beta"] <= params["beta_max"]))
        f = f[mask]; m = m[mask]

    if var_all is not None:
        var_vals.update(var_all); cvar_vals.update(cvar_all)
        mask = (var_vals.isna() | cvar_vals.isna() |
                ((var_vals >= params["var_max"]) & (cvar_vals >= params["cvar_max"])))
        f = f[mask]; m = m[mask]

    if len(f) == 0:
        return pd.Series(dtype=float), [], "filter_empty"

    # Step 2: Remove NaN core metrics
    core_cols = ["annualized_return", "annualized_vol", "sharpe_ratio", "alpha", "max_drawdown"]
    f = f.dropna(subset=core_cols)

    if len(f) == 0:
        return pd.Series(dtype=float), [], "nan_empty"

    # Core score
    raw_weights = {
        "return": params["weight_return"],
        "risk":   params["weight_risk"],
        "sharpe": params["weight_sharpe"],
        "alpha":  params["weight_alpha"],
        "mdd":    params["weight_mdd"],
    }
    total_w = sum(raw_weights.values())
    if total_w == 0:
        return pd.Series(dtype=float), [], "weight_zero"
    w = {k: v / total_w for k, v in raw_weights.items()}

    core_score = (
        w["return"] * _normalize(f["annualized_return"]) +
        w["risk"]   * _normalize_risk(f["annualized_vol"]) +
        w["sharpe"] * _normalize(f["sharpe_ratio"]) +
        w["alpha"]  * _normalize(f["alpha"]) +
        w["mdd"]    * _normalize_risk(f["max_drawdown"])
    )

    # Momentum adjustment
    adjustment = pd.Series(0.0, index=f.index)
    if params.get("use_momentum") and mom_all is not None:
        mom_vals.update(mom_all)
        m_valid = mom_vals.reindex(f.index)
        if m_valid.notna().any():
            norm_mom = _normalize(m_valid.fillna(m_valid.median()))
            if params["momentum_direction"] == "trend_following":
                adjustment += params["momentum_weight"] * norm_mom
            else:
                adjustment += params["momentum_weight"] * (1 - norm_mom)

    raw_score = core_score + adjustment
    mn, mx = raw_score.min(), raw_score.max()
    if mx == mn:
        final_score = pd.Series(0.5, index=raw_score.index)
    else:
        final_score = (raw_score - mn) / (mx - mn)

    return final_score, f.index.tolist(), "ok"
