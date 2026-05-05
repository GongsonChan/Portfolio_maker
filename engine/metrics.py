import numpy as np
import pandas as pd


def _portfolio_cumret(prices: pd.DataFrame, weights: dict,
                       start, end) -> pd.Series | None:
    tickers = [t for t in weights if t in prices.columns]
    if not tickers:
        return None
    p = prices.loc[start:end, tickers]
    r = p.pct_change().dropna()
    w = pd.Series({t: weights[t] for t in tickers})
    w /= w.sum()
    port_r = (r * w).sum(axis=1)
    return (1 + port_r).cumprod() - 1


def _daily_returns(cumret: pd.Series) -> pd.Series:
    return (cumret + 1).pct_change().dropna()


def _ann_return(cumret: pd.Series) -> float:
    # 백테스트 기간 총 누적 수익률
    if len(cumret) == 0:
        return np.nan
    return float(cumret.iloc[-1])


def _ann_return_annualized(cumret: pd.Series) -> float:
    # 연환산 수익률: (1 + total)^(252/n) - 1
    n = len(cumret)
    if n == 0:
        return np.nan
    total = float(cumret.iloc[-1])
    return (1 + total) ** (252 / n) - 1


def _ann_vol(cumret: pd.Series) -> float:
    r = _daily_returns(cumret)
    return float(r.std() * np.sqrt(252))


def _mdd(cumret: pd.Series) -> float:
    val = cumret + 1
    roll_max = val.cummax()
    dd = (val - roll_max) / roll_max
    return float(dd.min())


def _drawdown_series(cumret: pd.Series) -> pd.Series:
    val = cumret + 1
    roll_max = val.cummax()
    return (val - roll_max) / roll_max


def compute_portfolio_metrics(result: dict, macro: pd.DataFrame,
                               assets: pd.DataFrame, fundamentals: pd.DataFrame,
                               params: dict, prices: pd.DataFrame = None) -> dict:
    cumret = result["cumret"]
    weights = result["weights"]
    backtest_months = result["backtest_months"]

    end   = cumret.index.max()
    start = end - pd.DateOffset(months=backtest_months)

    rf = macro.loc[start:end, "fed_funds_rate"].mean() / 100 if "fed_funds_rate" in macro.columns else 0.0

    # 테스트 기간 수익률 (아웃오브샘플)
    ret     = _ann_return(cumret)
    ret_ann = _ann_return_annualized(cumret)

    # 스코어링/테스트 기간 경계 계산 (공통)
    if prices is not None:
        end_prices  = prices.index.max()
        test_start  = end_prices - pd.DateOffset(months=backtest_months)
        score_start = max(prices.index.min(),
                          test_start - pd.DateOffset(months=backtest_months))
    else:
        test_start = score_start = None

    # 스코어링 기간 수익률 (인샘플)
    if prices is not None and score_start is not None:
        score_cumret = _portfolio_cumret(prices, weights, score_start, test_start)
        ret_scoring  = _ann_return(score_cumret) if score_cumret is not None else np.nan
    else:
        ret_scoring = np.nan
    vol = _ann_vol(cumret)
    sharpe = (ret_ann - rf) / vol if vol > 0 else np.nan
    mdd = _mdd(cumret)

    # alpha vs benchmark
    bench_results = result.get("benchmarks", {})
    bench_key = "SPY" if params.get("allow_us") else "069500"
    alpha = np.nan
    if bench_key in bench_results:
        b_ret = _ann_return(bench_results[bench_key])
        port_r = cumret.pct_change().dropna()
        bench_r = bench_results[bench_key].pct_change().dropna()
        common = port_r.index.intersection(bench_r.index)
        if len(common) > 10:
            cov_ab = np.cov(port_r.loc[common], bench_r.loc[common])[0, 1]
            var_b  = bench_r.loc[common].var()
            beta   = cov_ab / var_b if var_b > 0 else np.nan
            alpha  = ret - beta * b_ret if not np.isnan(beta) else np.nan

    # dividend yield (weighted average)
    # US는 % 형식(예: 2.77 = 2.77%), KR은 소수점 형식(예: 0.0422 = 4.22%)으로 혼재
    # 0.20(20%) 초과 시 % 형식으로 판단해 /100 정규화
    fund_latest = fundamentals.sort_values("date").groupby("ticker").last()
    div_yield = 0.0
    for t, w in weights.items():
        if t in fund_latest.index:
            div = fund_latest.loc[t, "dividend_yield"]
            if np.isnan(div):
                continue
            if div > 0.20:  # % 형식 → 소수점으로 변환
                div = div / 100
            div_yield += w * div

    user_metrics = {
        "returns":          ret,        # 테스트 기간 누적 (아웃오브샘플)
        "returns_scoring":  ret_scoring, # 스코어링 기간 누적 (인샘플)
        "returns_annualized": ret_ann,
        "volatility":       vol,
        "sharpe_ratio":     sharpe,
        "alpha":            alpha,
        "max_drawdown":     mdd,
        "dividend_yield":   div_yield,
    }

    # preset metrics
    preset_metrics = {}
    for name, pr in result.get("presets", {}).items():
        pc = pr["cumret"]
        pr_ret     = _ann_return(pc)
        pr_ret_ann = _ann_return_annualized(pc)
        pr_vol = _ann_vol(pc)
        pr_sh  = (pr_ret_ann - rf) / pr_vol if pr_vol > 0 else np.nan
        pr_mdd = _mdd(pc)
        pr_alpha = np.nan
        if bench_key in bench_results:
            b_ret = _ann_return(bench_results[bench_key])
            port_r = pc.pct_change().dropna()
            bench_r = bench_results[bench_key].pct_change().dropna()
            common = port_r.index.intersection(bench_r.index)
            if len(common) > 10:
                cov_ab = np.cov(port_r.loc[common], bench_r.loc[common])[0, 1]
                var_b  = bench_r.loc[common].var()
                beta   = cov_ab / var_b if var_b > 0 else np.nan
                pr_alpha = pr_ret - beta * b_ret if not np.isnan(beta) else np.nan
        # 프리셋 배당수익률
        pr_div = 0.0
        for t, w in pr["weights"].items():
            if t in fund_latest.index:
                div = fund_latest.loc[t, "dividend_yield"]
                if not np.isnan(div):
                    if div > 0.20:
                        div = div / 100
                    pr_div += w * div

        # 프리셋 스코어링 기간 수익률
        pr_score_cumret = _portfolio_cumret(prices, pr["weights"], score_start, test_start) if prices is not None else None
        pr_ret_scoring  = _ann_return(pr_score_cumret) if pr_score_cumret is not None else np.nan

        preset_metrics[name] = {
            "returns":           pr_ret,
            "returns_scoring":   pr_ret_scoring,
            "returns_annualized": pr_ret_ann,
            "volatility": pr_vol, "sharpe_ratio": pr_sh,
            "alpha": pr_alpha, "max_drawdown": pr_mdd,
            "dividend_yield": pr_div,
        }

    bench_metrics = {}
    for bname, bc in bench_results.items():
        b_ret = _ann_return(bc)
        b_vol = _ann_vol(bc)
        b_sh  = (b_ret - rf) / b_vol if b_vol > 0 else np.nan
        b_mdd = _mdd(bc)
        bench_metrics[bname] = {
            "returns": b_ret, "returns_annualized": _ann_return_annualized(bc),
            "volatility": b_vol, "sharpe_ratio": b_sh,
            "alpha": np.nan, "max_drawdown": b_mdd,
        }

    # portfolio score (6-portfolio comparison) — 사용자·프리셋 모두 계산
    comparison = {"user": user_metrics, **preset_metrics, **bench_metrics}
    score = _portfolio_score(user_metrics, comparison, params)
    preset_scores = {n: _portfolio_score(pm, comparison, params) for n, pm in preset_metrics.items()}

    # 프리셋 점수 포함
    for n, ps in preset_scores.items():
        preset_metrics[n]["portfolio_score"] = ps

    return {
        "user":     {**user_metrics, "portfolio_score": score},
        "presets":  preset_metrics,
        "benchmarks": bench_metrics,
        "drawdown_series": _drawdown_series(cumret),
        "bench_drawdown": {k: _drawdown_series(v) for k, v in bench_results.items()},
        "preset_drawdown": {k: _drawdown_series(v["cumret"]) for k, v in result.get("presets", {}).items()},
        "preset_cumret": {k: v["cumret"] for k, v in result.get("presets", {}).items()},
    }


def _portfolio_score(user: dict, comparison: dict, params: dict) -> float:
    raw_w = {
        "return": params["weight_return"],
        "risk":   params["weight_risk"],
        "sharpe": params["weight_sharpe"],
        "alpha":  params["weight_alpha"],
        "mdd":    params["weight_mdd"],
    }
    total_w = sum(raw_w.values())
    if total_w == 0:
        return np.nan
    w = {k: v / total_w for k, v in raw_w.items()}

    metrics_map = {
        "return": "returns", "risk": "volatility",
        "sharpe": "sharpe_ratio", "alpha": "alpha", "mdd": "max_drawdown",
    }
    risk_keys = {"risk", "mdd"}

    scores = {}
    for key, col in metrics_map.items():
        vals = [m[col] for m in comparison.values() if col in m and not np.isnan(m[col])]
        if len(vals) < 2:
            scores[key] = 0.5
            continue
        mn, mx = min(vals), max(vals)
        user_val = user.get(col, np.nan)
        if np.isnan(user_val) or mx == mn:
            scores[key] = 0.5
        else:
            norm = (user_val - mn) / (mx - mn)
            scores[key] = 1 - norm if key in risk_keys else norm

    return sum(w[k] * scores[k] for k in w)
