import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def render_recommendation(rec: dict, assets: pd.DataFrame):
    if rec["status"] != "ok":
        status = rec["status"]
        if status in ("filter_empty", "nan_empty"):
            st.warning("현재 추천을 생성할 수 없습니다.\n\n필터 조건이 너무 강력해 통과하는 종목이 없습니다. 고급 설정에서 RSI·VaR·재무 필터를 완화하거나 비활성화해 주세요.")
        elif status == "selection_empty":
            st.warning("종목 선택에 실패했습니다. 선택 종목 수를 줄이거나 시장 범위를 넓혀보세요.")
        elif status == "insufficient_data":
            st.warning("추천 생성에 필요한 데이터가 부족합니다. 스코어링 기간을 줄여보세요.")
        else:
            st.warning(f"현재 추천을 생성할 수 없습니다. ({status})")
        return

    st.markdown("---")
    st.markdown("### 현재 포트폴리오 추천")
    st.info(
        f"**스코어링 기간**: {rec['period']}의 데이터로 종목을 평가해 추천합니다.  \n"
        f"사이드바의 **백테스트 기간(개월)** 슬라이더를 조정하면 스코어링 기간도 함께 변경됩니다.  \n"
        f"기준일: {rec['as_of']} | 과거 성과는 미래를 보장하지 않습니다."
    )

    selected = rec["selected"]
    weights  = rec["weights"]
    meta = assets.set_index("ticker")

    # 종목 카드
    cols = st.columns(min(len(selected), 5))
    for i, t in enumerate(selected):
        name  = str(meta.loc[t, "name"]) if t in meta.index and "name" in meta.columns else t
        if name == "nan":
            name = t
        w     = weights.get(t, 0) * 100
        sector = meta.loc[t, "sector"] if t in meta.index and "sector" in meta.columns else ""
        cols[i % 5].metric(label=name, value=f"{w:.1f}%", delta=t)

    st.markdown("<br>", unsafe_allow_html=True)

    tickers = list(weights.keys())
    vals    = [weights[t] * 100 for t in tickers]
    labels  = [str(meta.loc[t, "name"]) if t in meta.index else t for t in tickers]
    labels  = [l if l != "nan" else t for l, t in zip(labels, tickers)]

    # 파이 차트
    fig_pie = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.35,
        marker_colors=px.colors.qualitative.Pastel,
        textinfo="label+percent", textfont=dict(size=10),
    ))
    fig_pie.update_layout(
        title=dict(text="자산별 비중", font=dict(size=14, color="#111111")),
        height=420, paper_bgcolor="#F8FAFC",
        font=dict(color="#111111"),
        legend=dict(font=dict(color="#111111"), orientation="v"),
        template="plotly_white",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # 섹터 바 차트
    sector_w: dict[str, float] = {}
    for t, w in weights.items():
        if t in meta.index:
            atype = meta.loc[t, "asset_type"]
            sect  = meta.loc[t, "sector"] if atype == "stock" else atype
        else:
            sect = "기타"
        sector_w[sect] = sector_w.get(sect, 0) + w * 100

    fig_bar = go.Figure(go.Bar(
        x=list(sector_w.keys()),
        y=list(sector_w.values()),
        marker_color="#93C5FD",
        text=[f"{v:.1f}%" for v in sector_w.values()],
        textposition="outside",
    ))
    fig_bar.update_layout(
        title=dict(text="섹터별 비중", font=dict(size=14, color="#111111")),
        xaxis=dict(tickfont=dict(color="#111111", size=10)),
        yaxis=dict(title="비중 (%)", ticksuffix="%", tickfont=dict(color="#111111")),
        plot_bgcolor="#F8FAFC", paper_bgcolor="#F8FAFC",
        font=dict(color="#111111"),
        height=380, template="plotly_white",
    )
    st.plotly_chart(fig_bar, use_container_width=True)
