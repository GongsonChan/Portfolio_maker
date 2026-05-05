import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

COLORS = {
    "user":         "#2563EB",
    "aggressive":   "#DC2626",
    "balanced":     "#16A34A",
    "conservative": "#60A5FA",
    "SPY":          "#6B7280",
    "069500":       "#9CA3AF",
}

LEGEND_STYLE = dict(
    bgcolor="rgba(255,255,255,0.9)",
    bordercolor="#E5E7EB", borderwidth=1,
    font=dict(color="#111111", size=11),
)

TITLE_FONT = dict(size=15, color="#111111")

AXIS_STYLE = dict(
    tickfont=dict(color="#111111", size=11),
    linecolor="#555555",
    gridcolor="#E5E7EB",
)

GLOBAL_FONT = dict(color="#111111", family="sans-serif")
BASE_TEMPLATE = "plotly_white"


def _apply_axis_style(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(
        tickfont=dict(color="#111111", size=11),
        title_font=dict(color="#111111", size=12),
        linecolor="#555555", gridcolor="#E5E7EB",
    )
    fig.update_yaxes(
        tickfont=dict(color="#111111", size=11),
        title_font=dict(color="#111111", size=12),
        linecolor="#555555", gridcolor="#E5E7EB",
    )
    return fig


def chart_cumulative_return(result: dict, metrics: dict) -> go.Figure:
    fig = go.Figure(layout=go.Layout(template=BASE_TEMPLATE))

    # 스코어링/테스트 기간 경계선
    test_start = result.get("test_start")
    if test_start is not None:
        ts_str = pd.Timestamp(test_start).strftime("%Y-%m-%d")
        fig.add_vrect(
            x0=ts_str, x1=ts_str,
            line_width=1.5, line_color="#EF4444", line_dash="dash",
            annotation_text=" 테스트 시작", annotation_position="top left",
            annotation_font=dict(color="#EF4444", size=10),
        )

    cr = result["cumret"]
    fig.add_trace(go.Scatter(
        x=cr.index, y=cr.values * 100,
        name="내 포트폴리오",
        line=dict(color=COLORS["user"], width=4),
        visible=True
    ))

    bench_labels = {"SPY": "SPY (S&P500)", "069500": "069500 (KOSPI200)"}
    for bname, bc in result.get("benchmarks", {}).items():
        fig.add_trace(go.Scatter(
            x=bc.index, y=bc.values * 100,
            name=bench_labels.get(bname, bname),
            line=dict(color=COLORS.get(bname, "#9CA3AF"), width=1.5, dash="dot"),
            visible=True
        ))

    preset_labels = {
        "aggressive":   "공격형",
        "balanced":     "균형형",
        "conservative": "안정형",
    }
    for pname, pc in metrics.get("preset_cumret", {}).items():
        fig.add_trace(go.Scatter(
            x=pc.index, y=pc.values * 100,
            name=preset_labels.get(pname, pname),
            line=dict(color=COLORS.get(pname, "#888"), width=1.8),
            visible="legendonly"
        ))

    fig.update_layout(
        title=dict(text="누적 수익률", font=TITLE_FONT),
        legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.01, **LEGEND_STYLE),
        margin=dict(r=200),
        hovermode="x unified",
        plot_bgcolor="#F8FAFC", paper_bgcolor="#F8FAFC",
        font=GLOBAL_FONT,
        height=450, dragmode="zoom",
        xaxis=dict(
            title="날짜", **AXIS_STYLE,
            rangeslider=dict(
                visible=True, thickness=0.06,
                bgcolor="#D1D5DB", bordercolor="#6B7280", borderwidth=1,
            ),
            rangeselector=dict(
                font=dict(color="#111111", size=11),
                bgcolor="#E5E7EB",
                activecolor="#2563EB",
                buttons=[
                    dict(count=3,  label="3개월", step="month", stepmode="backward"),
                    dict(count=6,  label="6개월", step="month", stepmode="backward"),
                    dict(count=1,  label="1년",   step="year",  stepmode="backward"),
                    dict(count=2,  label="2년",   step="year",  stepmode="backward"),
                    dict(step="all", label="전체"),
                ]
            ),
        ),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", **AXIS_STYLE),
    )
    _apply_axis_style(fig)
    return fig


def chart_risk_return(result: dict, metrics: dict, assets: pd.DataFrame) -> go.Figure:
    fig = go.Figure(layout=go.Layout(template=BASE_TEMPLATE))
    meta = assets.set_index("ticker")

    type_colors = {"stock": "#93C5FD", "etf": "#FCD34D", "bond_proxy": "#6EE7B7"}

    test_feat = result.get("test_feat", {})
    for t in result.get("selected", []):
        if t not in test_feat:
            continue
        vol = test_feat[t]["annualized_vol"] * 100
        ret = test_feat[t]["annualized_return"] * 100
        atype = meta.loc[t, "asset_type"] if t in meta.index else "stock"
        color = type_colors.get(atype, "#93C5FD")
        name_label = str(meta.loc[t, "name"]) if t in meta.index and "name" in meta.columns else t
        if name_label == "nan":
            name_label = t
        fig.add_trace(go.Scatter(
            x=[vol], y=[ret], mode="markers",
            marker=dict(size=10, color=color),
            name=name_label, showlegend=False,
            hovertemplate=f"<b>{name_label}</b><br>변동성: %{{x:.1f}}%<br>수익률: %{{y:.1f}}%<extra></extra>",
        ))

    user_m = metrics.get("user", {})
    fig.add_trace(go.Scatter(
        x=[user_m.get("volatility", 0) * 100],
        y=[user_m.get("returns", 0) * 100],
        mode="markers+text",
        marker=dict(size=20, color=COLORS["user"], symbol="star"),
        text=["내 포트폴리오"], textposition="top center",
        textfont=dict(size=11, color=COLORS["user"]),
        name="내 포트폴리오",
    ))

    # 색상 범례용 더미 트레이스
    for atype, color, label in [("stock","#93C5FD","주식"), ("etf","#FCD34D","ETF"), ("bond_proxy","#6EE7B7","채권")]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=10, color=color),
            name=label, showlegend=True,
        ))

    fig.update_layout(
        title=dict(text="리스크-리턴 분포", font=TITLE_FONT),
        xaxis=dict(title="변동성 — 연환산 (%)", ticksuffix="%", **AXIS_STYLE),
        yaxis=dict(title="누적 수익률 — 백테스트 기간 (%)", ticksuffix="%", **AXIS_STYLE),
        plot_bgcolor="#F8FAFC", paper_bgcolor="#F8FAFC",
        font=GLOBAL_FONT,
        height=450,
        legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.01, **LEGEND_STYLE),
        margin=dict(r=120),
    )
    _apply_axis_style(fig)
    return fig


def chart_portfolio_weights(result: dict, assets: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    weights = result.get("weights", {})
    meta = assets.set_index("ticker")

    tickers = list(weights.keys())
    vals    = [weights[t] * 100 for t in tickers]
    labels  = []
    for t in tickers:
        n = str(meta.loc[t, "name"]) if t in meta.index and "name" in meta.columns else t
        labels.append(n if n != "nan" else t)

    pie = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.35,
        marker_colors=px.colors.qualitative.Pastel,
        textinfo="label+percent", textfont=dict(size=10),
    ))
    pie.update_layout(
        title=dict(text="자산별 비중", font=TITLE_FONT),
        height=450, paper_bgcolor="#F8FAFC",
        font=GLOBAL_FONT,
        legend=dict(font=dict(color="#111111")),
    )

    sector_w: dict[str, float] = {}
    for t, w in weights.items():
        if t in meta.index:
            atype = meta.loc[t, "asset_type"]
            sect  = meta.loc[t, "sector"] if atype == "stock" else atype
        else:
            sect = "기타"
        sector_w[sect] = sector_w.get(sect, 0) + w * 100

    bar = go.Figure(go.Bar(
        x=list(sector_w.keys()), y=list(sector_w.values()),
        marker_color="#93C5FD",
        text=[f"{v:.1f}%" for v in sector_w.values()],
        textposition="outside",
    ))
    bar.update_layout(
        title=dict(text="섹터별 비중", font=TITLE_FONT),
        xaxis=dict(title="섹터 / 자산군", **AXIS_STYLE),
        yaxis=dict(title="비중 (%)", ticksuffix="%", **AXIS_STYLE),
        plot_bgcolor="#F8FAFC", paper_bgcolor="#F8FAFC",
        font=GLOBAL_FONT,
        height=450,
    )
    return pie, bar


def chart_drawdown(result: dict, metrics: dict) -> go.Figure:
    fig = go.Figure(layout=go.Layout(template=BASE_TEMPLATE))

    test_start = result.get("test_start")
    if test_start is not None:
        ts_str = pd.Timestamp(test_start).strftime("%Y-%m-%d")
        fig.add_vrect(
            x0=ts_str, x1=ts_str,
            line_width=1.5, line_color="#EF4444", line_dash="dash",
            annotation_text=" 테스트 시작", annotation_position="top left",
            annotation_font=dict(color="#EF4444", size=10),
        )

    dd = metrics.get("drawdown_series")
    if dd is not None:
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values * 100,
            fill="tozeroy", name="내 포트폴리오",
            line=dict(color=COLORS["user"], width=3),
            fillcolor="rgba(37,99,235,0.15)",
            visible=True,
        ))

    bench_labels = {"SPY": "SPY (S&P500)", "069500": "069500 (KOSPI200)"}
    for bname, bdd in metrics.get("bench_drawdown", {}).items():
        fig.add_trace(go.Scatter(
            x=bdd.index, y=bdd.values * 100,
            name=bench_labels.get(bname, bname),
            line=dict(color=COLORS.get(bname, "#9CA3AF"), dash="dot", width=1.5),
            visible=True,
        ))

    preset_labels = {
        "aggressive":   "공격형",
        "balanced":     "균형형",
        "conservative": "안정형",
    }
    for pname, pdd in metrics.get("preset_drawdown", {}).items():
        fig.add_trace(go.Scatter(
            x=pdd.index, y=pdd.values * 100,
            name=preset_labels.get(pname, pname),
            line=dict(color=COLORS.get(pname, "#888"), width=1.8),
            visible="legendonly",
        ))

    fig.update_layout(
        title=dict(text="드로우다운", font=TITLE_FONT),
        xaxis=dict(title="날짜", **AXIS_STYLE),
        yaxis=dict(title="낙폭 (%)", ticksuffix="%", **AXIS_STYLE),
        legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.01, **LEGEND_STYLE),
        margin=dict(r=200),
        hovermode="x unified",
        plot_bgcolor="#F8FAFC", paper_bgcolor="#F8FAFC",
        font=GLOBAL_FONT,
        height=450, dragmode="zoom",
    )
    _apply_axis_style(fig)
    return fig


def chart_radar(metrics: dict, params: dict) -> go.Figure:
    categories = ["수익률", "안전성\n(저변동성)", "샤프비율", "알파\n(시장초과)", "낙폭방어\n(저MDD)"]

    def _radar_vals(m: dict, ref_list: list[dict]) -> list[float]:
        # returns, sharpe, alpha: 높을수록 좋음 → 그대로
        # volatility: 낮을수록 좋음 → 반전
        # max_drawdown: 음수이며 0에 가까울수록 좋음 → 반전 불필요 (norm 자체가 0=최악, 1=최선)
        keys = ["returns", "volatility", "sharpe_ratio", "alpha", "max_drawdown"]
        inv  = {1}  # volatility만 반전
        vals = []
        for i, k in enumerate(keys):
            all_v = [r[k] for r in ref_list if k in r and not np.isnan(r.get(k, float("nan")))]
            v = m.get(k, np.nan)
            if np.isnan(v) or len(all_v) < 2:
                vals.append(0.5)
                continue
            mn, mx = min(all_v), max(all_v)
            norm = (v - mn) / (mx - mn) if mx != mn else 0.5
            vals.append(1 - norm if i in inv else norm)
        return vals

    all_metrics = [metrics.get("user", {})] + list(metrics.get("presets", {}).values())
    all_metrics = [m for m in all_metrics if m]

    fig = go.Figure(layout=go.Layout(template=BASE_TEMPLATE))

    user_v = _radar_vals(metrics.get("user", {}), all_metrics)
    fig.add_trace(go.Scatterpolar(
        r=user_v + [user_v[0]], theta=categories + [categories[0]],
        fill="toself", name="내 포트폴리오",
        line=dict(color=COLORS["user"], width=2.5),
        fillcolor="rgba(37,99,235,0.15)",
    ))

    preset_labels = {"aggressive": "🔴 공격형", "balanced": "🟢 균형형", "conservative": "🔵 안정형"}
    for pname, pm in metrics.get("presets", {}).items():
        pv = _radar_vals(pm, all_metrics)
        fig.add_trace(go.Scatterpolar(
            r=pv + [pv[0]], theta=categories + [categories[0]],
            name=preset_labels.get(pname, pname),
            line=dict(color=COLORS.get(pname, "#888")),
            visible="legendonly",
        ))

    fig.update_layout(
        title=dict(text="Core Skills 레이더", font=TITLE_FONT),
        polar=dict(radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=9, color="#111111"))),
        legend=dict(**LEGEND_STYLE),
        paper_bgcolor="#F8FAFC",
        font=GLOBAL_FONT,
        height=450,
    )
    _apply_axis_style(fig)
    return fig
