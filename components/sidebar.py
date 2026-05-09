import streamlit as st
import pandas as pd


PRESET_PARAMS = {
    "aggressive": {
        "weight_return": 10, "weight_risk": 1, "weight_sharpe": 1,
        "weight_alpha": 8, "weight_mdd": 1,
        "num_assets": 6, "backtest_months": 36,
        "use_momentum": True, "momentum_direction": "trend_following",
        "momentum_window": 63, "momentum_weight": 0.20,
        "use_rsi_filter": False, "allow_us": True, "allow_kr": False,
    },
    "balanced": {
        "weight_return": 5, "weight_risk": 5, "weight_sharpe": 5,
        "weight_alpha": 4, "weight_mdd": 5,
        "num_assets": 10, "backtest_months": 36,
        "use_momentum": False, "use_rsi_filter": False,
        "allow_us": True, "allow_kr": True,
    },
    "conservative": {
        "weight_return": 1, "weight_risk": 9, "weight_sharpe": 8,
        "weight_alpha": 1, "weight_mdd": 10,
        "num_assets": 15, "backtest_months": 36,
        "use_momentum": False, "use_rsi_filter": True, "rsi_upper_bound": 65,
        "use_var_cvar_filter": True, "var_max": -0.02, "cvar_max": -0.04,
        "allow_us": True, "allow_kr": False,
    },
}

DEFAULT_PARAMS = PRESET_PARAMS["balanced"].copy()
DEFAULT_PARAMS.update({
    "use_pe_filter": False, "pe_max": 40,
    "use_pb_filter": False, "pb_max": 5,
    "use_roe_filter": False, "roe_min": 0.05,
    "use_div_filter": False, "div_min": 0.01,
    "use_de_filter": False, "de_max": 2.0,
    "use_rev_growth_filter": False, "rev_growth_min": -0.10,
    "use_mcap_filter": False, "mcap_percentile_min": 20,
    "use_volume_filter": False, "volume_percentile_min": 20,
    "use_var_cvar_filter": False, "var_max": -0.03, "cvar_max": -0.05,
    "use_beta_filter": False, "beta_min": 0.0, "beta_max": 2.0,
    "use_sector_limit": False, "sector_max": 2,
    "momentum_direction": "trend_following", "momentum_window": 126,
    "momentum_weight": 0.15,
    "show_etf_options": True, "show_bond_options": True,
    "forced_assets_weight": 0.3,
    "forced_stocks": [], "forced_assets": [],
    "rsi_upper_bound": 70,
})


def render_sidebar(assets: pd.DataFrame) -> dict:
    p = {}

    st.sidebar.markdown("## 투자 전략 설정")

    # Preset buttons
    st.sidebar.markdown("**전략 프리셋**")
    col1, col2, col3 = st.sidebar.columns(3)
    preset_choice = st.session_state.get("preset_choice", "balanced")
    if col1.button("공격형", use_container_width=True,
                   type="primary" if preset_choice == "aggressive" else "secondary"):
        st.session_state.preset_choice = "aggressive"
        st.session_state.preset_loaded = True
        st.rerun()
    if col2.button("균형형", use_container_width=True,
                   type="primary" if preset_choice == "balanced" else "secondary"):
        st.session_state.preset_choice = "balanced"
        st.session_state.preset_loaded = True
        st.rerun()
    if col3.button("안정형", use_container_width=True,
                   type="primary" if preset_choice == "conservative" else "secondary"):
        st.session_state.preset_choice = "conservative"
        st.session_state.preset_loaded = True
        st.rerun()

    base = PRESET_PARAMS.get(preset_choice, PRESET_PARAMS["balanced"])
    defaults = {**DEFAULT_PARAMS, **base}

    st.sidebar.divider()

    # Core parameters
    st.sidebar.markdown("**핵심 파라미터**")

    p["num_assets"] = st.sidebar.slider(
        "선택 종목 수", 1, 20, defaults["num_assets"],
        help=(
            "포트폴리오에 담을 종목 수를 설정합니다.\n"
            "시스템은 점수 순으로 선택하되, 상관관계가 낮은 종목을 우선해 분산 효과를 높입니다.\n\n"
            "늘리면\n→ 더 많은 종목에 분산 투자, 리스크 감소, 수익률 평균화\n\n"
            "줄이면\n→ 소수 핵심 종목 집중, 수익률 높을 수 있지만 변동성 증가"
        ))

    p["scoring_months"] = st.sidebar.slider(
        "스코어링 기간 (개월)", 1, 30, defaults.get("scoring_months", 24),
        help=(
            "종목 점수 계산에 사용할 과거 데이터 기간(M)입니다.\n"
            "이 기간의 수익률·변동성 등으로 종목을 평가합니다.\n\n"
            "늘리면\n→ 장기 추세 반영, 안정적 종목 선호\n\n"
            "줄이면\n→ 최근 흐름 반영, 빠른 시장 변화에 반응"
        ))
    sm = p["scoring_months"]
    yrs_s, mths_s = divmod(sm, 12)
    st.sidebar.caption(f"스코어링: 약 {yrs_s}년 {mths_s}개월" if yrs_s else f"스코어링: 약 {mths_s}개월")

    DATA_MONTHS = 60  # 보유 데이터 총 기간
    max_test = max(1, min(30, DATA_MONTHS - sm))
    p["test_months"] = st.sidebar.slider(
        "테스트 기간 (개월)", 1, max_test,
        min(defaults.get("test_months", 12), max_test),
        help=(
            "포트폴리오 성과를 평가할 아웃오브샘플 기간(N)입니다.\n"
            "스코어링 기간 바로 이후 N개월을 성과 측정에 사용합니다.\n"
            "스코어링 + 테스트 ≤ 60개월 (데이터 한계)\n\n"
            "늘리면\n→ 장기 성과 검증\n\n"
            "줄이면\n→ 최근 성과 중심 평가"
        ))
    tm = p["test_months"]
    yrs_t, mths_t = divmod(tm, 12)
    st.sidebar.caption(f"테스트: 약 {yrs_t}년 {mths_t}개월" if yrs_t else f"테스트: 약 {mths_t}개월")

    # 합계 표시
    total = sm + tm
    if total > DATA_MONTHS:
        st.sidebar.error(f"스코어링({sm}) + 테스트({tm}) = {total}개월 → 데이터 한계({DATA_MONTHS}개월) 초과")
    else:
        st.sidebar.caption(f"총 {total}개월 사용 / 보유 {DATA_MONTHS}개월")

    # 하위 호환 (기존 코드가 backtest_months 사용)
    p["backtest_months"] = p["test_months"]

    st.sidebar.markdown("**Core 지표 중요도** (숫자가 클수록 중요)")
    p["weight_return"] = st.sidebar.slider("수익률 중요도", 0, 10, defaults["weight_return"],
        help=(
            "계산: 연환산 수익률 = (1 + 일평균수익률)^252 - 1\n"
            "백테스트 기간 동안 해당 종목이 연 평균 몇 % 올랐는지를 나타냅니다.\n\n"
            "높이면\n→ 과거에 많이 오른 종목 우선 선택, 공격적 포트폴리오\n\n"
            "낮추면\n→ 수익률보다 안전성·효율성을 더 중시"
        ))
    p["weight_risk"] = st.sidebar.slider("안정성(저변동성) 중요도", 0, 10, defaults["weight_risk"],
        help=(
            "계산: 연환산 변동성 = 일별수익률 표준편차 × √252\n"
            "이 값은 '변동성을 얼마나 싫어하냐'입니다. 높을수록 가격 흔들림이 적은 종목을 선호합니다.\n\n"
            "주의: 공격형=1(변동성 감수), 안정형=9(변동성 강하게 회피)\n\n"
            "높이면\n→ 가격이 안정적인 종목 우선 선택 (안정형 성향)\n\n"
            "낮추면\n→ 변동성이 커도 감수, 수익률 등 다른 지표를 더 중시 (공격형 성향)"
        ))
    p["weight_sharpe"] = st.sidebar.slider("샤프비율 중요도", 0, 10, defaults["weight_sharpe"],
        help=(
            "계산: 샤프비율 = (수익률 - 무위험수익률) / 변동성\n"
            "위험 한 단위당 얼마나 많은 초과 수익을 얻었는지 나타내는 효율성 지표입니다.\n"
            "같은 변동성이면 수익률이 높을수록, 같은 수익률이면 변동성이 낮을수록 높아집니다.\n\n"
            "높이면\n→ 수익과 안전성이 균형 잡힌 종목 우선, 리스크 대비 효율 좋은 포트폴리오\n\n"
            "낮추면\n→ 효율성보다 절대 수익률이나 다른 지표를 더 중시"
        ))
    p["weight_alpha"] = st.sidebar.slider("알파(시장초과수익) 중요도", 0, 10, defaults["weight_alpha"],
        help=(
            "계산: 알파 = 종목 수익률 - 베타 × 시장(벤치마크) 수익률\n"
            "시장 전체 흐름을 제외하고 해당 종목만의 독자적인 성과를 나타냅니다.\n"
            "시장이 올랐을 때 같이 오른 건 알파가 아니고, 시장과 무관하게 추가로 얻은 수익이 알파입니다.\n\n"
            "높이면\n→ 시장을 이긴 종목, 독자적인 경쟁력 있는 종목 우선 선택\n\n"
            "낮추면\n→ 시장 초과 성과보다 다른 지표를 더 중시"
        ))
    p["weight_mdd"] = st.sidebar.slider("최대낙폭(MDD) 중요도", 0, 10, defaults["weight_mdd"],
        help=(
            "계산: MDD = (저점 - 직전 고점) / 직전 고점 × 100\n"
            "백테스트 기간 중 주가가 고점 대비 최대로 얼마나 떨어졌는지 나타냅니다.\n"
            "예) MDD -30% → 한때 최고점에서 30%까지 하락한 구간이 있었다는 의미입니다.\n\n"
            "높이면\n→ 큰 폭 하락 없이 꾸준한 종목 우선, 손실 방어 중심의 안정적 포트폴리오\n\n"
            "낮추면\n→ 일시적인 큰 하락을 감수하고 다른 지표를 더 중시"
        ))

    total_w = sum([p["weight_return"], p["weight_risk"],
                   p["weight_sharpe"], p["weight_alpha"], p["weight_mdd"]])
    if total_w == 0:
        st.sidebar.error("⚠️ 모든 중요도가 0입니다. 최소 1개 이상 설정해주세요.")
    else:
        total = total_w
        pcts = {
            "수익률": p["weight_return"] / total * 100,
            "리스크": p["weight_risk"] / total * 100,
            "샤프":   p["weight_sharpe"] / total * 100,
            "알파":   p["weight_alpha"] / total * 100,
            "낙폭":   p["weight_mdd"] / total * 100,
        }
        st.sidebar.caption("  |  ".join([f"{k}: {v:.0f}%" for k, v in pcts.items()]))

    st.sidebar.divider()

    # Market selection
    st.sidebar.markdown("**시장 선택** (최소 1개 필수)")
    p["allow_us"] = st.sidebar.checkbox("미국 주식", value=defaults.get("allow_us", True))
    p["allow_kr"] = st.sidebar.checkbox("한국 주식", value=defaults.get("allow_kr", True))
    if not p["allow_us"] and not p["allow_kr"]:
        st.sidebar.error("⚠️ 미국 또는 한국 시장 중 하나 이상 선택해야 합니다.")

    # Forced stocks search
    st.sidebar.divider()
    st.sidebar.markdown("**종목 고정 선택 (선택사항)**")

    stock_pool = assets[(assets["asset_type"] == "stock") & (assets["is_active"] == True)]
    stock_options = {
        f"{row['ticker']} | {row.get('name', '')} | {row.get('sector', '')} | {row.get('market', '')}": row["ticker"]
        for _, row in stock_pool.iterrows()
    }
    forced_stock_labels = st.sidebar.multiselect(
        "주식 직접 선택 (검색 가능)",
        options=list(stock_options.keys()),
        help="점수와 무관하게 반드시 포함할 주식을 선택합니다."
    )
    p["forced_stocks"] = [stock_options[l] for l in forced_stock_labels]

    # Forced ETF/bond
    etf_bond_options = []
    BOND_ETFS = {"TLT": "미국 20년 국채 ETF", "IEF": "미국 7-10년 국채 ETF",
                 "LQD": "투자등급 회사채 ETF", "HYG": "고수익 회사채 ETF"}
    COMMODITY_ETFS = {"GLD": "금 ETF", "SLV": "은 ETF", "CPER": "구리 ETF", "USO": "원유 ETF"}
    INDEX_ETFS = {"SPY": "S&P500 ETF", "QQQ": "나스닥100 ETF", "069500": "KODEX 200"}

    forced_asset_labels = st.sidebar.multiselect(
        "헷징 자산 선택 (ETF/채권)",
        options=([f"{t} | 채권 ETF | {d}" for t, d in BOND_ETFS.items()] +
                 [f"{t} | 상품 ETF | {d}" for t, d in COMMODITY_ETFS.items()] +
                 [f"{t} | 지수 ETF | {d}" for t, d in INDEX_ETFS.items()]),
        help="헷징 목적으로 포트폴리오에 반드시 포함할 ETF/채권을 선택합니다."
    )
    p["forced_assets"] = [lbl.split(" | ")[0] for lbl in forced_asset_labels]

    all_forced = p["forced_stocks"] + p["forced_assets"]
    if all_forced:
        p["forced_assets_weight"] = st.sidebar.slider(
            "강제 자산 전체 비중", 0.0, 1.0, defaults["forced_assets_weight"], 0.05,
            help=f"강제 자산 {len(all_forced)}개에 할당할 비중 합계. 균등 분배됩니다.\n"
                 f"예) 0.3 → 각 {0.3/len(all_forced)*100:.0f}% / 나머지 주식 {(1-0.3)*100:.0f}%")
        w_each = p["forced_assets_weight"] / len(all_forced)
        st.sidebar.caption(
            f"강제 자산 각 {w_each*100:.1f}% / 나머지 그리디 주식 {(1-p['forced_assets_weight'])*100:.1f}%"
        )
    else:
        p["forced_assets_weight"] = 0.0

    # Advanced settings
    st.sidebar.divider()
    with st.sidebar.expander("고급 설정"):
        st.markdown("**모멘텀**")
        p["use_momentum"] = st.checkbox("모멘텀 반영", value=defaults.get("use_momentum", False),
            help="최근 수익률 추세를 점수에 반영합니다.")
        if p["use_momentum"]:
            p["momentum_direction"] = st.selectbox(
                "모멘텀 방향",
                ["trend_following", "mean_reversion"],
                index=0 if defaults.get("momentum_direction") == "trend_following" else 1,
                format_func=lambda x: "추세추종 (오르는 종목)" if x == "trend_following" else "역추세 (내린 종목)",
                help="추세추종: 최근 오른 종목 선호\n역추세: 최근 내린 종목 선호 (반등 기대)")
            max_mom_window = p["backtest_months"] * 21
            p["momentum_window"] = st.slider("모멘텀 기간 (일)", 5, min(252, max_mom_window),
                min(defaults.get("momentum_window", 126), max_mom_window),
                help="짧을수록 단기 반응, 길수록 장기 추세")
            p["momentum_weight"] = st.slider("모멘텀 강도", 0.0, 0.3,
                defaults.get("momentum_weight", 0.15), 0.05)
        else:
            p["momentum_direction"] = defaults.get("momentum_direction", "trend_following")
            p["momentum_window"] = defaults.get("momentum_window", 126)
            p["momentum_weight"] = 0.0

        st.markdown("---")
        st.markdown("**RSI 필터**")
        p["use_rsi_filter"] = st.checkbox("RSI 과매수 필터",
            value=defaults.get("use_rsi_filter", False),
            help="RSI가 기준 초과인 종목(과매수 상태)을 제외합니다.")
        p["rsi_upper_bound"] = st.slider("RSI 상한", 50, 90,
            defaults.get("rsi_upper_bound", 70),
            help="RSI가 이 값 초과 종목은 선택 제외.\n70 이상 = 과매수 신호") if p["use_rsi_filter"] else 70

        st.markdown("---")
        st.markdown("**재무 필터**")
        p["use_pe_filter"] = st.checkbox("PER 상한 필터", value=defaults.get("use_pe_filter", False),
            help="PER = 주가 ÷ 주당순이익. 낮을수록 이익 대비 저평가. 이 값 초과 종목을 제외합니다.\n↑ 높이면: 고성장 종목도 허용\n↓ 낮추면: 저평가 종목만 선택")
        p["pe_max"] = st.slider("PER 상한", 5, 100, defaults.get("pe_max", 40)) if p["use_pe_filter"] else 999

        p["use_pb_filter"] = st.checkbox("PBR 상한 필터", value=defaults.get("use_pb_filter", False),
            help="PBR = 주가 ÷ 주당순자산. 낮을수록 자산 대비 저평가. 이 값 초과 종목을 제외합니다.\n↑ 높이면: 고평가 종목도 허용\n↓ 낮추면: 저평가 종목만 선택")
        p["pb_max"] = st.slider("PBR 상한", 0.5, 20.0, defaults.get("pb_max", 5.0)) if p["use_pb_filter"] else 999

        p["use_roe_filter"] = st.checkbox("ROE 하한 필터", value=defaults.get("use_roe_filter", False),
            help="수익성 낮은 기업을 제외합니다.")
        p["roe_min"] = st.slider("ROE 하한", 0.0, 0.30, defaults.get("roe_min", 0.05), 0.01) if p["use_roe_filter"] else -999

        p["use_div_filter"] = st.checkbox("배당수익률 하한 필터", value=defaults.get("use_div_filter", False),
            help="무배당 또는 저배당 종목을 제외합니다.\n↑ 높이면: 배당을 많이 주는 종목만 선택\n↓ 낮추면: 소액 배당 종목도 허용")
        p["div_min"] = st.slider("배당수익률 하한", 0.0, 0.10, defaults.get("div_min", 0.01), 0.005) if p["use_div_filter"] else -999

        p["use_de_filter"] = st.checkbox("부채비율(D/E) 상한 필터", value=defaults.get("use_de_filter", False),
            help="과다 부채 기업을 제외합니다.")
        p["de_max"] = st.slider("D/E 상한", 0.5, 10.0, defaults.get("de_max", 2.0), 0.5) if p["use_de_filter"] else 999

        p["use_rev_growth_filter"] = st.checkbox("매출성장률 하한 필터", value=defaults.get("use_rev_growth_filter", False))
        p["rev_growth_min"] = st.slider("매출성장률 하한", -0.5, 0.5, defaults.get("rev_growth_min", -0.1), 0.05) if p["use_rev_growth_filter"] else -999

        st.markdown("---")
        st.markdown("**유동성 필터**")
        p["use_mcap_filter"] = st.checkbox("시가총액 하위 제외", value=defaults.get("use_mcap_filter", False),
            help="시가총액 하위 N% 소형주를 제외합니다.")
        p["mcap_percentile_min"] = st.slider("시가총액 하위 N% 제외", 0, 50,
            defaults.get("mcap_percentile_min", 20)) if p["use_mcap_filter"] else 0

        p["use_volume_filter"] = st.checkbox("거래량 하위 제외", value=defaults.get("use_volume_filter", False),
            help="거래량이 적어 사고팔기 어려운 비유동성 종목을 제외합니다.\n↑ 높이면: 거래 활발한 종목만 선택\n↓ 낮추면: 소량 거래 종목도 허용")
        p["volume_percentile_min"] = st.slider("거래량 하위 N% 제외", 0, 50,
            defaults.get("volume_percentile_min", 20)) if p["use_volume_filter"] else 0

        st.markdown("---")
        st.markdown("**리스크 필터**")
        p["use_var_cvar_filter"] = st.checkbox("VaR/CVaR 꼬리 리스크 필터",
            value=defaults.get("use_var_cvar_filter", False),
            help="하루 최대 손실이 너무 큰 종목을 제외합니다.")
        if p["use_var_cvar_filter"]:
            p["var_max"]  = st.slider("VaR 상한 (일별)", -0.30, -0.01, defaults.get("var_max", -0.03), 0.01,
                help="95% VaR 상한. 예) -0.03 → 하루 3% 초과 손실 종목 제외")
            p["cvar_max"] = st.slider("CVaR 상한 (일별)", -0.50, -0.01, defaults.get("cvar_max", -0.05), 0.01,
                help="CVaR = 최악의 날 평균 손실 상한")
        else:
            p["var_max"] = -0.99; p["cvar_max"] = -0.99

        p["use_beta_filter"] = st.checkbox("베타 범위 필터", value=defaults.get("use_beta_filter", False),
            help="시장 민감도(베타) 범위를 설정합니다.\n베타<1: 방어적, 베타>1: 공격적")
        if p["use_beta_filter"]:
            p["beta_min"] = st.slider("베타 하한", 0.0, 2.0, defaults.get("beta_min", 0.0), 0.1)
            p["beta_max"] = st.slider("베타 상한", 0.5, 3.0, defaults.get("beta_max", 2.0), 0.1)
        else:
            p["beta_min"] = 0.0; p["beta_max"] = 99.0

        st.markdown("---")
        p["use_sector_limit"] = st.checkbox("섹터 집중도 제한", value=defaults.get("use_sector_limit", False),
            help="같은 섹터 종목이 너무 많이 선택되는 것을 방지합니다.")
        p["sector_max"] = st.slider("섹터별 최대 종목 수", 1, 5,
            defaults.get("sector_max", 2)) if p["use_sector_limit"] else 99

    return p
