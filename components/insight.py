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
        "당신은 투자 포트폴리오 분석 전문가입니다.\n"
        "아래 포트폴리오 데이터를 바탕으로 다음 규칙에 따라 인사이트를 생성하세요:\n"
        "1. 핵심 성과 요약 1문장 (수익률, 리스크 중심)\n"
        "2. 벤치마크 또는 프리셋 대비 특징 1문장\n"
        "3. 개선 또는 주의사항 제안 1문장\n"
        "- 전문 용어는 간단히 설명 병기\n"
        "- 수치는 반드시 포함\n"
        "- 한국어로 작성\n"
        "- 총 3문장 이내"
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
