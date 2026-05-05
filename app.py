import streamlit as st
import pandas as pd
from pathlib import Path

from engine.backtest import run_all
from engine.metrics import compute_portfolio_metrics
from components.sidebar import render_sidebar
from components.charts import (
    chart_cumulative_return, chart_risk_return,
    chart_portfolio_weights, chart_drawdown, chart_radar,
)
from components.table import render_table
from components.insight import render_insight
from components.recommendation import render_recommendation
from engine.recommendation import get_current_recommendation

DATA = Path(__file__).parent / "data"

st.set_page_config(
    page_title="Rule-Based Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data():
    prices  = pd.read_csv(DATA / "Prices.csv",        index_col=0, parse_dates=True)
    volume  = pd.read_csv(DATA / "Volume.csv",         index_col=0, parse_dates=True)
    fundam  = pd.read_csv(DATA / "Fundamentals.csv",   parse_dates=["date"])
    macro   = pd.read_csv(DATA / "macro.csv",          index_col=0, parse_dates=True)
    assets  = pd.read_csv(DATA / "Assets.csv",         encoding="utf-8-sig")
    corr    = pd.read_csv(DATA / "correlation_matrix.csv", index_col=0)
    return prices, volume, fundam, macro, assets, corr


prices, volume, fundamentals, macro, assets, corr_matrix = load_data()


# ── 튜토리얼 ──────────────────────────────────────────────────────────────────
TUTORIAL_STEPS = [
    ("전략 선택",
     "먼저 투자 성향에 맞는 전략을 선택하세요.\n"
     "**공격형** (고수익 추구) / **균형형** (리스크·수익 균형) / **안정형** (리스크 최소화)\n"
     "왼쪽 사이드바 상단 버튼에서 선택할 수 있습니다."),
    ("종목 수 & 기간 설정",
     "**선택 종목 수**와 **백테스트 기간**을 슬라이더로 설정하세요.\n"
     "종목 수가 많을수록 분산투자, 기간이 길수록 장기 성과를 평가합니다."),
    ("분석 실행",
     "설정 완료 후 사이드바 하단의 **[▶ 분석 실행]** 버튼을 눌러주세요.\n"
     "결과가 차트와 테이블로 자동 표시됩니다."),
    ("차트 확인",
     "**누적 수익률 그래프**에서 내 포트폴리오와 벤치마크를 비교하세요.\n"
     "차트 범례를 클릭하면 특정 시리즈를 켜고 끌 수 있습니다."),
    ("고급 설정",
     "사이드바의 **[⚙️ 고급 설정]** 을 펼치면 RSI 필터, 재무 필터, 모멘텀 등\n"
     "더 세밀한 조건을 설정할 수 있습니다."),
]


def render_tutorial():
    step = st.session_state.get("tutorial_step", 0)
    if step == 0:
        return
    idx = step - 1
    if idx >= len(TUTORIAL_STEPS):
        st.session_state.tutorial_step = 0
        return
    title, desc = TUTORIAL_STEPS[idx]
    with st.container():
        st.info(f"**[튜토리얼 {step}/{len(TUTORIAL_STEPS)}] {title}**\n\n{desc}")
        c1, c2, c3 = st.columns([1, 1, 5])
        if c1.button("← 이전", disabled=(step == 1)):
            st.session_state.tutorial_step -= 1
            st.rerun()
        if step < len(TUTORIAL_STEPS):
            if c2.button("다음 →"):
                st.session_state.tutorial_step += 1
                st.rerun()
        else:
            if c2.button("✅ 시작하기"):
                st.session_state.tutorial_step = 0
                st.session_state.run_analysis = True
                st.rerun()
        if c3.button("닫기"):
            st.session_state.tutorial_step = 0
            st.rerun()


# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
div[data-testid="stButton"] button[kind="secondary"].tutorial-btn {
    background-color: #22C55E;
    color: white;
    border: none;
    font-weight: 600;
}
/* 사용법 버튼만 초록색 */
div.tutorial-btn-wrap button {
    background-color: #22C55E !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

col_title, col_tut = st.columns([6, 1])
col_title.title("Rule-Based Investment Dashboard")
with col_tut:
    st.markdown('<div class="tutorial-btn-wrap">', unsafe_allow_html=True)
    if st.button("사용법 보기", type="secondary", use_container_width=True):
        st.session_state.tutorial_step = 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

render_tutorial()

# ── 사이드바 ──────────────────────────────────────────────────────────────────
params = render_sidebar(assets)
params["preset_choice"] = st.session_state.get("preset_choice", "balanced")

# 분석 실행 버튼
st.sidebar.divider()
run_btn = st.sidebar.button("분석 실행", type="primary", use_container_width=True)

if run_btn or st.session_state.get("run_analysis"):
    st.session_state.run_analysis = False

    # 유효성 검사
    if not params.get("allow_us") and not params.get("allow_kr"):
        st.error("⚠️ 미국 또는 한국 시장 중 하나 이상을 선택해야 합니다.")
        st.stop()

    total_w = sum([params["weight_return"], params["weight_risk"],
                   params["weight_sharpe"], params["weight_alpha"], params["weight_mdd"]])
    if total_w == 0:
        st.error("⚠️ 모든 중요도가 0입니다. 최소 1개 이상 설정해주세요.")
        st.stop()

    with st.spinner("분석 중..."):
        result = run_all(prices, macro, assets, fundamentals, corr_matrix, params)

    if result["status"] == "filter_empty":
        st.error("⚠️ 선택된 조건에 맞는 종목이 없습니다. 필터가 너무 강력합니다!")
        st.stop()
    elif result["status"] == "nan_empty":
        st.error("⚠️ 스탯 계산 가능한 종목이 없습니다. 백테스트 기간을 늘려보세요.")
        st.stop()
    elif result["status"] == "weight_zero":
        st.error("⚠️ 가중치 합이 0입니다.")
        st.stop()
    elif result["status"] != "ok":
        st.error(f"분석 실패: {result['status']}")
        st.stop()

    metrics = compute_portfolio_metrics(result, macro, assets, fundamentals, params, prices)
    st.session_state.result   = result
    st.session_state.metrics  = metrics
    st.session_state.params   = params
    st.session_state.insight  = None  # 분석 실행 시 인사이트 초기화

# ── 결과 표시 ─────────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.info("왼쪽 사이드바에서 설정 후 [분석 실행] 버튼을 눌러주세요.")
    if st.button("기본값으로 바로 실행 (균형형)"):
        st.session_state.run_analysis = True
        st.rerun()
    st.stop()

result  = st.session_state.result
metrics = st.session_state.metrics
params  = st.session_state.params

# 선택 종목 요약
st.markdown("### 선택된 포트폴리오")
selected = result.get("selected", [])
weights  = result.get("weights", {})
meta = assets.set_index("ticker")

cols = st.columns(min(len(selected), 5))
for i, t in enumerate(selected):
    name  = meta.loc[t, "name"] if t in meta.index and "name" in meta.columns else t
    name  = str(name) if name and str(name) != "nan" else t
    w     = weights.get(t, 0) * 100
    is_forced = t in params.get("forced_stocks", []) or t in params.get("forced_assets", [])
    pin   = " [고정]" if is_forced else ""
    cols[i % 5].metric(
        label=f"{name}{pin}",
        value=f"{w:.1f}%",
        delta=t,
    )

st.divider()

CHART_HELP = {
    "cumret":    "투자 시작 시점을 0%로 기준 삼아 현재까지 누적으로 얼마나 올랐는지 보여줍니다.\n범례를 클릭해 다른 전략과 비교하고, 드래그로 확대할 수 있습니다.",
    "riskreturn":"X축(오른쪽)이 변동성이 높을수록 위험, Y축(위쪽)이 수익률이 높을수록 유리합니다.\n★ 별이 내 포트폴리오이며, 왼쪽 위에 가까울수록 우수합니다.",
    "weights":   "포트폴리오 내 각 자산의 비중을 시각화합니다.\n자산별 탭과 섹터별 탭으로 전환해볼 수 있습니다.",
    "drawdown":  "고점 대비 얼마나 떨어졌는지를 나타냅니다. 0%에 가까울수록 안정적이며,\n음수가 클수록 낙폭이 심한 구간이 있었다는 의미입니다.",
    "radar":     "5가지 핵심 지표를 하나의 거미줄 차트로 표현합니다.\n바깥쪽으로 넓게 퍼질수록 해당 지표가 우수하다는 의미입니다.",
}

def _chart_header(title: str, help_key: str):
    st.markdown(f"**{title}**", help=CHART_HELP[help_key])

_chart_header("누적 수익률", "cumret")
st.plotly_chart(chart_cumulative_return(result, metrics), use_container_width=True)

_chart_header("리스크-리턴 분포", "riskreturn")
st.plotly_chart(chart_risk_return(result, metrics, assets), use_container_width=True)

_chart_header("포트폴리오 비중", "weights")
pie, bar = chart_portfolio_weights(result, assets)
tab1, tab2 = st.tabs(["자산별 비중", "섹터별 비중"])
with tab1:
    st.plotly_chart(pie, use_container_width=True)
with tab2:
    st.plotly_chart(bar, use_container_width=True)

_chart_header("드로우다운", "drawdown")
st.plotly_chart(chart_drawdown(result, metrics), use_container_width=True)

_chart_header("Core Skills 레이더", "radar")
st.plotly_chart(chart_radar(metrics, params), use_container_width=True)

# Table
st.markdown("### 지표 요약")
render_table(metrics,
             backtest_months=params.get("test_months", params.get("backtest_months", 12)),
             scoring_months=params.get("scoring_months", 24))

# 현재 포트폴리오 추천 (백테스트 결과 기반, 최근 데이터 전체 사용)
with st.spinner("현재 포트폴리오 추천 생성 중..."):
    rec = get_current_recommendation(prices, macro, assets, fundamentals, corr_matrix, params)
render_recommendation(rec, assets)

# Insight - 분석 실행 시 한 번만 생성, 이후 캐시 표시
st.markdown("### AI 인사이트")
if st.session_state.get("insight") is None:
    with st.spinner("AI 인사이트 생성 중..."):
        insight_text = render_insight(metrics, result, params, assets_df=assets)
        st.session_state.insight = insight_text
    st.info(insight_text)
else:
    st.info(st.session_state.insight)
