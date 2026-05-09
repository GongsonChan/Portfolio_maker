import numpy as np
import pandas as pd


def select_assets(scores: pd.Series, corr_matrix: pd.DataFrame,
                  assets: pd.DataFrame, params: dict) -> tuple[list, dict]:
    forced_stocks = params.get("forced_stocks", [])
    forced_etfs   = params.get("forced_assets", [])
    all_forced    = forced_stocks + forced_etfs
    num_assets    = params.get("num_assets", 10)

    if len(all_forced) > num_assets:
        num_assets = len(all_forced)

    meta = assets.set_index("ticker")

    # step 0: forced assets
    selected = list(all_forced)
    universe = [t for t in scores.index if t not in forced_stocks]

    # step 1: if no forced, pick top scorer
    if len(selected) == 0:
        if len(universe) == 0:
            return [], {}
        selected = [scores.reindex(universe).idxmax()]

    # step 2: greedy correlation-aware selection
    # forced_assets_weight=1.0이면 그리디 스킵 (강제 자산만으로 포트폴리오 구성)
    forced_w_check = params.get("forced_assets_weight", 0.3) if all_forced else 0.0
    if forced_w_check >= 1.0:
        num_assets = len(selected)  # 그리디 추가 없음

    remaining = [t for t in universe if t not in selected]
    warnings  = []

    while len(selected) < num_assets and remaining:
        best_t, best_s = None, -np.inf
        for t in remaining:
            corr_candidates = [
                corr_matrix.loc[t, s]
                for s in selected
                if t in corr_matrix.index and s in corr_matrix.columns
            ]
            max_corr = max(corr_candidates) if corr_candidates else 0.0
            max_corr = np.clip(max_corr, -1, 1)

            if t not in scores.index:
                continue
            adj = scores[t] * (1 - max_corr)

            # sector limit (forced assets excluded)
            if params.get("use_sector_limit"):
                sector_max = params.get("sector_max", 2)
                t_sector = meta.loc[t, "sector"] if t in meta.index else None
                greedy_sel = [s for s in selected if s not in all_forced]
                sector_count = sum(
                    1 for s in greedy_sel
                    if s in meta.index and meta.loc[s, "sector"] == t_sector
                )
                if sector_count >= sector_max:
                    continue

            if adj > best_s:
                best_s, best_t = adj, t

        if best_t is None:
            break
        selected.append(best_t)
        remaining.remove(best_t)

    if len(selected) < num_assets:
        warnings.append(f"필터 조건으로 인해 {len(selected)}개 종목만 선택되었습니다.")

    # weight assignment
    forced_w = params.get("forced_assets_weight", 0.3) if all_forced else 0.0
    greedy_sel = [t for t in selected if t not in all_forced]
    weights: dict[str, float] = {}

    if all_forced:
        w_each = forced_w / len(all_forced)
        for t in all_forced:
            weights[t] = w_each

    remaining_w = 1.0 - forced_w
    if greedy_sel:
        s_vals = scores.reindex(greedy_sel).fillna(0)
        total  = s_vals.sum()
        for t in greedy_sel:
            weights[t] = (s_vals[t] / total * remaining_w) if total > 0 else remaining_w / len(greedy_sel)

    total_check = sum(weights.values())
    if total_check > 0:
        weights = {t: w / total_check for t, w in weights.items()}

    return selected, weights
