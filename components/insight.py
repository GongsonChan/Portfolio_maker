import streamlit as st
import json


def _get_api_key() -> str:
    try:
        return st.secrets["GPT"]
    except Exception:
        try:
            from dotenv import load_dotenv
            import os
            load_dotenv()
            return os.getenv("GPT", "")
        except Exception:
            return ""


def render_insight(metrics: dict, result: dict, params: dict) -> str:
    api_key = _get_api_key()
    if not api_key:
        return "GPT API 키가 설정되지 않았습니다. .streamlit/secrets.toml에 GPT 키를 입력해주세요."

    user = metrics.get("user", {})
    presets = metrics.get("presets", {})
    benchmarks = metrics.get("benchmarks", {})

    selected_assets = []
    for t in result.get("selected", []):
        from engine.backtest import run_backtest
        selected_assets.append({
            "ticker": t,
            "weight": round(result["weights"].get(t, 0) * 100, 1),
        })

    payload = {
        "strategy": params.get("preset_choice", "custom"),
        "num_assets": len(result.get("selected", [])),
        "selected_assets": selected_assets,
        "returns":        round(user.get("returns", 0) * 100, 2),
        "volatility":     round(user.get("volatility", 0) * 100, 2),
        "sharpe_ratio":   round(user.get("sharpe_ratio", 0), 2),
        "alpha":          round(user.get("alpha", 0) * 100, 2),
        "max_drawdown":   round(user.get("max_drawdown", 0) * 100, 2),
        "dividend_yield": round(user.get("dividend_yield", 0) * 100, 2),
        "portfolio_score": round(user.get("portfolio_score", 0), 3),
        "benchmark_returns": {k: round(v.get("returns", 0) * 100, 2) for k, v in benchmarks.items()},
        "preset_comparison": {
            k: {
                "returns":      round(v.get("returns", 0) * 100, 2),
                "sharpe_ratio": round(v.get("sharpe_ratio", 0), 2),
                "max_drawdown": round(v.get("max_drawdown", 0) * 100, 2),
            }
            for k, v in presets.items()
        },
    }

    system_prompt = (
        "당신은 정량 투자 전략을 해석하는 퀀트 애널리스트입니다.\n\n"
        "아래 포트폴리오 데이터를 바탕으로 단순 요약이 아닌 '해석 중심 인사이트'를 작성하세요.\n\n"
        "규칙:\n"
        "1. 이 포트폴리오의 핵심 전략 성향을 먼저 설명 (예: 고수익/고위험, 저변동성, 샤프 중심 등)\n"
        "2. 왜 이런 결과가 나왔는지 '지표 조합 관점'에서 설명 (가중치, 필터 영향)\n"
        "3. 벤치마크 대비 우위/열위를 '이유와 함께' 설명\n"
        "4. 현재 구조에서 발생 가능한 리스크를 구체적으로 지적\n"
        "5. 반드시 종목 구성 특징 (섹터/집중도/자산군)을 1개 이상 언급\n\n"
        "제약:\n"
        "- 단순 수치 나열 금지\n"
        "- '좋다/나쁘다' 단정 금지 → 이유 포함\n"
        "- 3~4문장\n"
        "- 한국어"
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"인사이트를 불러올 수 없습니다.\n\n오류: {e}"
