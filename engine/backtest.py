import numpy as np
import pandas as pd

from engine.scoring import compute_features, score_assets
from engine.selection import select_assets

PRESET_FIXED = {
    # 비교군 고정 파라미터 — 사용자 설정과 무관하게 항상 동일
    "aggressive": {
        "weight_return": 10, "weight_risk": 1, "weight_sharpe": 1,
        "weight_alpha": 8, "weight_mdd": 1,
        "num_assets": 6,
        "allow_us": True, "allow_kr": False,
        "use_momentum": True, "momentum_direction": "trend_following",
        "momentum_window": 63, "momentum_weight": 0.20,
        "use_rsi_filter": False,
        "use_var_cvar_filter": False, "use_beta_filter": False,
        "use_pe_filter": False, "use_pb_filter": False,
        "use_roe_filter": False, "use_div_filter": False,
        "use_de_filter": False, "use_rev_growth_filter": False,
        "use_mcap_filter": False, "use_volume_filter": False,
        "use_sector_limit": False,
    },
    "balanced": {
        "weight_return": 5, "weight_risk": 5, "weight_sharpe": 5,
        "weight_alpha": 4, "weight_mdd": 5,
        "num_assets": 10,
        "allow_us": True, "allow_kr": True,
        "use_momentum": False, "momentum_direction": "trend_following",
        "momentum_window": 126, "momentum_weight": 0.0,
        "use_rsi_filter": False,
        "use_var_cvar_filter": False, "use_beta_filter": False,
        "use_pe_filter": False, "use_pb_filter": False,
        "use_roe_filter": False, "use_div_filter": False,
        "use_de_filter": False, "use_rev_growth_filter": False,
        "use_mcap_filter": False, "use_volume_filter": False,
        "use_sector_limit": False,
    },
    "conservative": {
        "weight_return": 1, "weight_risk": 9, "weight_sharpe": 8,
        "weight_alpha": 1, "weight_mdd": 10,
        "num_assets": 15,
        "allow_us": True, "allow_kr": False,
        "use_momentum": False, "momentum_direction": "trend_following",
        "momentum_window": 126, "momentum_weight": 0.0,
        "use_rsi_filter": True, "rsi_upper_bound": 65,
        "use_var_cvar_filter": True, "var_max": -0.02, "cvar_max": -0.04,
        "use_beta_filter": False,
        "use_pe_filter": False, "use_pb_filter": False,
        "use_roe_filter": False, "use_div_filter": False,
        "use_de_filter": False, "use_rev_growth_filter": False,
        "use_mcap_filter": False, "use_volume_filter": False,
        "use_sector_limit": False,
    },
}


def run_backtest(prices: pd.DataFrame, weights: dict, backtest_months: int) -> pd.Series:
    end   = prices.index.max()
    start = end - pd.DateOffset(months=backtest_months)
    p = prices.loc[start:end, [t for t in weights if t in prices.columns]]
    r = p.pct_change().dropna()

    w_series = pd.Series(weights)
    w_series = w_series.reindex(r.columns).fillna(0)
    if w_series.sum() > 0:
        w_series /= w_series.sum()

    port_ret = (r * w_series).sum(axis=1)
    cumret   = (1 + port_ret).cumprod() - 1
    return cumret


def run_all(prices: pd.DataFrame, macro: pd.DataFrame, assets: pd.DataFrame,
            fundamentals: pd.DataFrame, corr_matrix: pd.DataFrame,
            params: dict) -> dict:
    backtest_months = params["backtest_months"]

    # 사용자 포트폴리오
    feat = compute_features(prices, macro, assets, fundamentals, backtest_months, params)
    scores, universe, status = score_assets(feat, assets, params, prices, backtest_months)

    if status != "ok":
        return {"status": status}

    selected, weights = select_assets(scores, corr_matrix, assets, params)
    if not selected:
        return {"status": "selection_empty"}

    user_cum = run_backtest(prices, weights, backtest_months)

    # 벤치마크
    bench_results = {}
    for bench in ["SPY", "069500"]:
        if bench in prices.columns:
            w_b = {bench: 1.0}
            bench_results[bench] = run_backtest(prices, w_b, backtest_months)

    # 프리셋 포트폴리오 — 고유 파라미터 고정 + 기간/데이터만 사용자와 공유
    preset_results = {}
    for preset_name, preset_fixed in PRESET_FIXED.items():
        # 기간(scoring_months, test_months, backtest_months)과 forced_assets만 사용자 값 사용
        # 전략 파라미터(weights, filters, allow_kr, num_assets 등)는 프리셋 고유 값으로 고정
        p_params = {
            **preset_fixed,
            "scoring_months":  params.get("scoring_months", backtest_months),
            "test_months":     backtest_months,
            "backtest_months": backtest_months,
            # forced_assets_weight=1.0이면 프리셋은 강제 종목 없이 자기 전략대로 계산
            # (비교 의미가 사라지므로)
            "forced_stocks":   [] if params.get("forced_assets_weight", 0.0) >= 1.0 else params.get("forced_stocks", []),
            "forced_assets":   [] if params.get("forced_assets_weight", 0.0) >= 1.0 else params.get("forced_assets", []),
            "forced_assets_weight": 0.0 if params.get("forced_assets_weight", 0.0) >= 1.0 else params.get("forced_assets_weight", 0.0),
            # 나머지 임시 파라미터 기본값
            "beta_min": 0.0, "beta_max": 99.0,
            "sector_max": 99,
            "pe_max": 999, "pb_max": 999, "roe_min": -999,
            "div_min": -999, "de_max": 999, "rev_growth_min": -999,
            "mcap_percentile_min": 0, "volume_percentile_min": 0,
            "var_max":  preset_fixed.get("var_max", -0.99),
            "cvar_max": preset_fixed.get("cvar_max", -0.99),
            "rsi_upper_bound": preset_fixed.get("rsi_upper_bound", 100),
        }
        p_scores, p_universe, p_status = score_assets(feat, assets, p_params, prices, backtest_months)
        if p_status != "ok":
            continue
        p_selected, p_weights = select_assets(p_scores, corr_matrix, assets, p_params)
        if p_selected:
            preset_results[preset_name] = {
                "cumret":   run_backtest(prices, p_weights, backtest_months),
                "selected": p_selected,
                "weights":  p_weights,
            }

    # 테스트 기간 개별 종목 수익률/변동성 (스캐터용, 누수 없음)
    end_p       = prices.index.max()
    test_start  = end_p - pd.DateOffset(months=backtest_months)
    test_prices = prices.loc[test_start:end_p]
    test_ret    = test_prices.pct_change(fill_method=None)
    test_feat   = {}
    for t in selected:
        if t not in test_ret.columns:
            continue
        r = test_ret[t].dropna()
        if len(r) < 5:
            continue
        test_feat[t] = {
            "annualized_return": float((1 + r).prod() - 1),
            "annualized_vol":    float(r.std() * (252 ** 0.5)),
        }

    return {
        "status":         "ok",
        "selected":       selected,
        "weights":        weights,
        "cumret":         user_cum,
        "feat":           feat,
        "test_feat":      test_feat,   # 테스트 기간 개별 종목 지표
        "test_start":     test_start,  # 차트 경계선용
        "scores":         scores,
        "benchmarks":     bench_results,
        "presets":        preset_results,
        "backtest_months": backtest_months,
    }
