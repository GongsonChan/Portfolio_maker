============================================================
Skills.md — Rule-Based Investment Engine Specification
============================================================

목적:
- 사용자 입력 + 데이터 → 포트폴리오 생성 + 성과 평가

1. INPUT
============================================================
시스템에 들어오는 데이터 및 사용자 입력 정의
[INPUT]

---------- Data Sources ----------

price_data:           Prices.csv           (일별 종가, wide format: date × ticker)
volume_data:          Volume.csv           (일별 거래량, wide format: date × ticker)
fundamental_data:     Fundamentals.csv     (분기별 재무지표: PE, PB, ROE, EPS 등)
macro_data:           macro.csv            (일별 거시지표: 금리, 국채수익률, 스프레드)
asset_metadata:       Assets.csv           (자산 메타: ticker, name, asset_type, sector, market, is_active)
correlation_data:     correlation_matrix.csv (수익률 기반 자산 간 상관계수 행렬, Greedy 선택에 사용)

---------- User Parameters ----------
scoring_months (M):
  type: int
  range: [6, 36]
  unit: 개월(month)
  description: "종목 점수 계산에 사용할 과거 데이터 기간. 스코어링 기간: [end-N-M, end-N]"

test_months (N):
  type: int
  range: [3, 36]
  unit: 개월(month)
  description: "아웃오브샘플 성과 평가 기간. 테스트 기간: [end-N, end]"
  제약: scoring_months + test_months ≤ 60 (데이터 총 기간)

# 하위 호환: backtest_months = test_months (내부 처리용)

num_assets:
  type: int
  range: [1, 20]
  description: "선택할 종목 개수"

weight_return:
  type: int
  range: [0, 10]
  description: "수익률 중요도 (상대값)"

weight_risk:
  type: int
  range: [0, 10]
  description: "리스크 중요도 (상대값, 패널티)"

weight_sharpe:
  type: int
  range: [0, 10]
  description: "수익/리스크 균형 중요도 (상대값)"

weight_alpha:
  type: int
  range: [0, 10]
  description: "시장 초과수익 중요도 (상대값)"

weight_mdd:
  type: int
  range: [0, 10]
  description: "최대 낙폭 중요도 (상대값, 패널티)"

정규화: 내부 계산 시 weight[i] = raw_value[i] / sum(raw_values) → [0, 1] 자동 변환
조건: 모든 값이 0이면 안 됨 (합 = 0 → 정규화 불가)

strategy(default option):
  type: categorical
  values: [aggressive, balanced, conservative]
  description: "프리셋 선택 시 위 가중치를 자동으로 설정. 사용자가 직접 조정도 가능"

---------- Advanced Parameters (선택적) ----------
use_momentum:
  type: bool
  default: false
  description: "모멘텀 지표 반영 여부"

momentum_direction:
  type: categorical
  values: [trend_following, mean_reversion]
  default: trend_following
  description:
    trend_following  → 최근에 오른 종목 선호 (추세추종)
    mean_reversion   → 최근에 내린 종목 선호 (반등 기대)

momentum_window:
  type: int
  range: [5, 252]
  unit: 일(day)
  default: 126
  제약:
    backtest_months 먼저 설정한 경우: momentum_window ≤ backtest_months × 21 로 상한 제한
    momentum_window 먼저 설정한 경우: backtest_months 설정 시 충돌하면 momentum_window를
      자동으로 backtest_months × 21 로 하향 조정
  description: "모멘텀 계산 기간. 짧을수록 단기 반응, 길수록 장기 추세"

momentum_weight:
  type: float
  range: [0, 0.3]
  description: "모멘텀 보정 강도. core_score에 추가 보정값으로 작용"

use_rsi_filter:
  type: bool
  default: false
  description: "RSI 기반 과매수 종목 제외 여부, rsi는 상대강도지수"
rsi_upper_bound:
  type: float
  default: 70
  range: [50, 90]
  description: "RSI가 이 값 초과인 종목은 선택 대상에서 제외"

use_pe_filter:
  type: bool
  default: false
  description: "PER 상한 필터. 고평가 종목 제외"
pe_max:
  type: float
  default: 40
  range: [5, 100]
  description: "PER 상한선. 이 값 초과 종목 제외"

use_pb_filter:
  type: bool
  default: false
  description: "PBR 상한 필터. 고평가 종목 제외"
pb_max:
  type: float
  default: 5
  range: [0.5, 20]
  description: "PBR 상한선. 이 값 초과 종목 제외"

use_roe_filter:
  type: bool
  default: false
  description: "ROE 하한 필터. 수익성 낮은 종목 제외"
roe_min:
  type: float
  default: 0.05
  range: [0, 0.30]
  description: "ROE 하한선. 이 값 미만 종목 제외"

use_div_filter:
  type: bool
  default: false
  description: "배당수익률 하한 필터. 무배당 또는 저배당 종목 제외"
div_min:
  type: float
  default: 0.01
  range: [0, 0.10]
  description: "배당수익률 하한선. 이 값 미만 종목 제외"

use_de_filter:
  type: bool
  default: false
  description: "부채비율(D/E) 상한 필터. 과도한 부채 종목 제외"
de_max:
  type: float
  default: 2.0
  range: [0.5, 10]
  description: "부채비율 상한선. 이 값 초과 종목 제외"

use_rev_growth_filter:
  type: bool
  default: false
  description: "매출 성장률 하한 필터. 심한 역성장 종목 제외"
rev_growth_min:
  type: float
  default: -0.10
  range: [-0.50, 0.50]
  description: "매출 성장률 하한선. 이 값 미만 종목 제외"

use_mcap_filter:
  type: bool
  default: false
  description: "시가총액 하위 N% 필터. 소형주 유동성 리스크 제거"
mcap_percentile_min:
  type: int
  default: 20
  range: [0, 50]
  unit: percentile (%)
  description: "시가총액 하위 N% 종목 제외. US/KR 각 시장 내에서 독립적으로 적용"

use_volume_filter:
  type: bool
  default: false
  description: "거래량 하위 N% 종목 제외. 비유동성 종목 거래 리스크 제거"
volume_percentile_min:
  type: int
  default: 20
  range: [0, 50]
  unit: percentile (%)
  description: "거래량 하위 N% 종목 제외. 시장 내에서 독립적으로 적용"

use_var_cvar_filter:
  type: bool
  default: false
  description: "꼬리 리스크 필터. VaR·CVaR 동시 설정 시에만 활성화"
var_max:
  type: float
  default: -0.03
  range: [-0.30, -0.01]
  unit: 일별 수익률
  description: "95% VaR 상한. 예) -0.03 → 하루 3% 초과 손실 가능 종목 제외"
cvar_max:
  type: float
  default: -0.05
  range: [-0.50, -0.01]
  unit: 일별 수익률
  description: "95% CVaR 상한. VaR 초과 시 평균 손실 상한. var_max보다 작아야 함"

use_beta_filter:
  type: bool
  default: false
  description: "베타 범위 필터. 시장 민감도 기준으로 종목 제외"
beta_min:
  type: float
  default: 0.0
  range: [0.0, 2.0]
  description: "베타 하한. 예) 0.5 → 방어적 성향 (시장보다 덜 움직이는 종목만)"
beta_max:
  type: float
  default: 2.0
  range: [0.5, 3.0]
  description: "베타 상한. 예) 1.5 → 공격적 성향 제한 (고베타 종목 제외)"

use_sector_limit:
  type: bool
  default: false
  description: "섹터 집중도 제한. 동일 섹터 종목이 과도하게 선택되는 것을 방지"
sector_max:
  type: int
  default: 2
  range: [1, 5]
  description: "동일 섹터 내 최대 선택 종목 수. Greedy 선택 시 초과되면 해당 종목 스킵"

---------- 그리디 대상 주식 시장 [복수 선택 가능, 최소 1개 필수] ----------
allow_us:
  type: bool
  default: true
  description: "미국 주식을 그리디 선택 대상에 포함할지 여부"
allow_kr:
  type: bool
  default: true
  description: "한국 주식을 그리디 선택 대상에 포함할지 여부 (KOSPI)"
제약: allow_us == False AND allow_kr == False 이면 실행 불가
  → UI 오류 메시지: "미국 또는 한국 시장 중 하나 이상을 선택해야 합니다."

---------- 헷징 자산 선택 목록 노출 여부 ----------
# ETF / 채권은 그리디 대상이 아님. forced_assets UI에서 선택 목록으로만 표시됨
show_etf_options:
  type: bool
  default: true
  description: "forced_assets 선택 UI에서 상품·지수 ETF 목록 표시 여부 (GLD, SLV, CPER, USO, SPY, QQQ, 069500)"
show_bond_options:
  type: bool
  default: true
  description: "forced_assets 선택 UI에서 채권 ETF 목록 표시 여부 (TLT, IEF, LQD, HYG)"

forced_stocks:
  type: list[str]
  default: []
  description: "점수와 무관하게 반드시 포함할 주식 직접 선택. universe(is_active stock) 내 종목만 허용"
  ui: 검색창 + 전체 목록 리스트 (ticker + name + sector 표시)
  note: "forced_stocks + forced_assets 합산 수가 num_assets 초과 시 num_assets 자동 상향 조정"

forced_assets_weight:
  type: float
  range: [0.0, 0.8]
  default: 0.3
  description: "forced_stocks + forced_assets 전체에 할당할 비중 합계. 1:1 균등 분배"
  note: "예) forced_stocks 1개 + forced_assets 1개 → 각 15% (0.3/2)"

forced_assets:
  type: list[str]
  default: []
  description: "점수와 무관하게 포트폴리오에 반드시 포함할 자산 직접 선택. 미선택 시 완전 그리디"
  selectable_options:
    채권 ETF:
      - TLT   # 미국 20년 국채 ETF          [?]
      - IEF   # 미국 7-10년 국채 ETF        [?]
      - LQD   # 투자등급 회사채 ETF          [?]
      - HYG   # 고수익(하이일드) 회사채 ETF  [?]
    상품 ETF:
      - GLD   # 금 ETF                      [?]
      - SLV   # 은 ETF                      [?]
      - CPER  # 구리 ETF                    [?]
      - USO   # 원유 ETF                    [?]
    지수 ETF:
      - SPY   # S&P500 지수 ETF             [?]
      - QQQ   # 나스닥100 지수 ETF          [?]
      - 069500 # KODEX 200 (한국 코스피200) [?]
  ui_note: "복수 선택 가능. 선택하지 않아도 무방"


============================================================
2. FEATURE ENGINEERING
============================================================
원시 데이터 → 분석용 feature 생성
[FEATURE_ENGINEERING]

returns:
  formula: r_t = (P_t / P_{t-1}) - 1

cumulative_return_period:
  formula: (1 + r_0)(1 + r_1)...(1 + r_n) - 1   (백테스트 기간 총 누적 수익률)
  note: 연환산(annualized) 아님 — 실제 보유 기간의 총 수익률

annualized_return:
  formula: (1 + cumulative_return_period)^(252/n) - 1   (참고용 연환산)
  note: 기하평균 방식. 테이블에 보조 지표로 함께 표시

annualized_volatility:
  formula: std(r_t) × sqrt(252)

sharpe_ratio:
  formula: (annualized_return - rf) / annualized_volatility
  rf: macro.csv → fed_funds_rate 백테스트 기간 평균값 (연율 기준)

max_drawdown:
  formula: min((P_t - max(P_0..P_t)) / max(P_0..P_t))

beta:
  formula: cov(r_asset, r_benchmark) / var(r_benchmark)
  benchmark: SPY (US 자산), 069500 (KR 자산)
  note: 혼합 포트폴리오는 시장 비중에 따라 가중 평균 beta 사용

alpha:
  formula: annualized_return - beta × benchmark_annualized_return

momentum:
  formula: r_t[-momentum_window:t]   (사용자 설정 window 기간 수익률)
  note: trend_following이면 높을수록 좋음 / mean_reversion이면 낮을수록 좋음

rsi:
  window: 14
  formula:
    RS = avg_gain / avg_loss (14일 기준)
    RSI = 100 - (100 / (1 + RS))

var_95:
  formula: percentile(r_t, 5)   (95% VaR, 역수익률 기준)

cvar_95:
  formula: mean(r_t [r_t < var_95])

avg_volume:
  formula: mean(volume_t, window=60)   (60일 평균 거래량, volume_filter 기준값 계산용)

dividend_yield:
  source: Fundamentals.csv → dividend_yield 컬럼 직접 참조 (계산 불필요)
  note: 가장 최근 분기 값 사용. 없으면 0 처리


============================================================
3. ASSET SCORING
============================================================
개별 자산에 대해 Core Skills 기반 점수를 계산
[ASSET_SCORING]

# 초기 universe 정의 (ETF/채권은 애초에 포함하지 않음)
universe = [t for t in Assets.csv
            if is_active[t] == True
            and asset_type[t] == "stock"
            and ((allow_us and market[t] == "US")
              or (allow_kr and market[t] == "KR"))]
# → 이후 모든 필터는 stock만 대상으로 작동. ETF/bond_proxy는 forced_assets로만 편입

---------- Normalization ----------
# 정규화 기준: 아래 모든 필터를 통과한 최종 universe 종목들의 min/max 사용
각 지표는 Min-Max 정규화 후 점수 계산:
  normalized = (x - min) / (max - min)   → [0, 1]

리스크 지표(volatility, MDD, VaR, CVaR)는 낮을수록 좋으므로:
  normalized_risk = 1 - (x - min) / (max - min)

---------- Core Score Formula (Step 2 이후 실행) ----------
# 아래 공식은 Step 1 → Step 1.5 → Step 2 필터링 완료 후 적용
core_score =
  weight_return  × normalized(annualized_return)
+ weight_risk    × normalized_risk(annualized_volatility)
+ weight_sharpe  × normalized(sharpe_ratio)
+ weight_alpha   × normalized(alpha)
+ weight_mdd     × normalized_risk(max_drawdown)

조건: 내부 계산 시 raw_value[i] / sum(raw_values) 로 자동 정규화 → 합 = 1 보장

---------- Step 1: 펀더멘털 필터 (Fundamentals.csv 정적 데이터 기반) ----------
# 계산 비용 없는 정적 지표로 먼저 universe 축소
# NaN 종목은 해당 필터 통과 (재무제표 미공시 주식 보호)

if use_pe_filter:
  universe = [t for t in universe if isnan(pe_ratio[t]) or pe_ratio[t] <= pe_max]

if use_pb_filter:
  universe = [t for t in universe if isnan(pb_ratio[t]) or pb_ratio[t] <= pb_max]

if use_roe_filter:
  universe = [t for t in universe if isnan(roe[t]) or roe[t] >= roe_min]

if use_div_filter:
  universe = [t for t in universe if isnan(div[t]) or div[t] >= div_min]

if use_de_filter:
  universe = [t for t in universe if isnan(de[t]) or de[t] <= de_max]

if use_rev_growth_filter:
  universe = [t for t in universe if isnan(rev_growth[t]) or rev_growth[t] >= rev_growth_min]

if use_mcap_filter:
  mcap_threshold[market] = percentile(market_cap[시장별], mcap_percentile_min)
  universe = [t for t in universe if market_cap[t] >= mcap_threshold[market[t]]]

if use_volume_filter:
  volume_threshold[market] = percentile(avg_volume[시장별], volume_percentile_min)
  universe = [t for t in universe if avg_volume[t] >= volume_threshold[market[t]]]

---------- Step 1.5: 기술적 지표 계산 → 지표 필터 적용 ----------
# Step 1 통과 종목만 대상으로 Prices.csv 기반 지표 계산 (계산 비용 절감)
# RSI, beta, VaR, CVaR, momentum → 필터링 후 Step 2 점수 계산에도 재사용

for t in universe:
  beta[t]   = cov(r_t, r_benchmark) / var(r_benchmark)  # 항상 계산 (alpha에 필요)
  if use_rsi_filter:
    rsi[t]    = 계산 (14일 기준)
  if use_var_cvar_filter:
    var_95[t] = percentile(r_t, 5)
    cvar_95[t]= mean(r_t [r_t < var_95[t]])
  if use_momentum:
    momentum[t] = r_t[-momentum_window:t]

if use_rsi_filter:
  universe = [t for t in universe if isnan(rsi[t]) or rsi[t] <= rsi_upper_bound]

if use_beta_filter:
  universe = [t for t in universe
              if isnan(beta[t]) or (beta[t] >= beta_min and beta[t] <= beta_max)]

if use_var_cvar_filter:
  universe = [t for t in universe
              if isnan(var_95[t]) or isnan(cvar_95[t])
              or (var_95[t] >= var_max and cvar_95[t] >= cvar_max)]

# 최종 필터 후 universe 공백 체크
if len(universe) == 0:
  → UI 메시지: "선택된 조건에 맞는 종목이 없습니다. 필터가 너무 강력합니다!"
  → 분석 중단, 사용자에게 필터 완화 유도

---------- Step 2: 점수 계산 (모든 필터 통과 종목만) ----------
# 핵심 지표 NaN 종목 제거 (정규화 오염 방지)
universe = [t for t in universe
            if not any(isnan(m) for m in
               [annualized_return[t], annualized_volatility[t],
                sharpe_ratio[t], alpha[t], max_drawdown[t]])]

if len(universe) == 0:
  → UI 메시지: "스탯 계산 가능한 종목이 없습니다. 백테스트 기간을 늘려보세요."
  → 분석 중단

adjustment = 0

if use_momentum:
  # Step 1.5에서 계산된 momentum[t] 재사용 (중복 계산 없음)
  # 정규화 기준: 필터링 통과 종목들의 momentum min/max
  if momentum_direction == trend_following:
    adjustment += momentum_weight × normalized(momentum)       # 많이 오른 종목에 가산점
  elif momentum_direction == mean_reversion:
    adjustment += momentum_weight × (1 - normalized(momentum)) # 많이 내린 종목에 가산점

# 최종 점수: core_score + adjustment 후 [0,1] 재정규화
raw_score = core_score + adjustment
if max(raw_score) == min(raw_score):
  final_asset_score = 0.5   # 모든 종목 동점 시 중간값 처리
else:
  final_asset_score = (raw_score - min(raw_score)) / (max(raw_score) - min(raw_score))


============================================================
4. ASSET SELECTION (Greedy Correlation-Aware)
============================================================
개별 점수 + 상관관계를 동시에 고려하여 N개 자산 선택
[ASSET_SELECTION]

---------- 알고리즘 ----------
input:
  scores: {ticker → final_asset_score}   # stock만 존재
  corr_matrix: correlation_matrix.csv
  num_assets: N (사용자 입력)
  universe: ASSET SCORING에서 초기 정의 및 필터링 완료된 stock universe
  # ETF / bond_proxy 는 forced_assets로만 편입, 그리디 대상 아님

step 0: 강제포함 자산 먼저 선택
  all_forced = forced_stocks + forced_assets  # 주식 + ETF/채권 합산
  if len(all_forced) > num_assets:
    num_assets = len(all_forced)   # 자동 상향 조정, 사용자에게 알림
  selected = all_forced  # 점수/상관관계/필터 무시하고 선택 확정
  # forced_stocks는 ASSET SCORING 필터를 우회 (수동 선택 = 필터 면제)
  universe = universe - forced_stocks  # 그리디 대상에서 제외
  # forced_assets(ETF/채권)는 원래부터 universe에 없으므로 별도 제외 불필요

step 1: 점수 1위 자산 선택 (all_forced 없으면 여기서 시작)
  if len(selected) == 0:
    selected = [argmax(scores)]
  # forced_assets가 있으면 selected 이미 채워진 상태 → step 2로 바로 진행

step 2: 반복 (N개 채울 때까지, 또는 remaining_assets 소진 시 종료)
  # universe < (num_assets - len(selected)) 이면 가능한 만큼만 선택 후 종료
  # → UI 알림: "필터 조건으로 인해 {len(selected)}개 종목만 선택되었습니다."
  remaining_assets = universe - selected
  for each candidate in remaining_assets:
    max_corr = max(corr(candidate, s) for s in selected)
    adjusted_score = scores[candidate] × (1 - max_corr)

  next = argmax(adjusted_score)

  if use_sector_limit:
    # forced_stocks + forced_assets 모두 sector_limit 계산에서 제외 (수동 선택 자산)
    greedy_selected = [s for s in selected if s not in all_forced]
    sector_count = count(s for s in greedy_selected if sector[s] == sector[next])
    if sector_count >= sector_max:
      skip next, try next best candidate

  selected.append(next)

output: selected (N개 티커 리스트)

---------- 비중 배분 ----------
# forced 자산 비중 (forced_stocks + forced_assets 합산)
all_forced = forced_stocks + forced_assets
if len(all_forced) > 0:
  weight[i] = forced_assets_weight / len(all_forced)   # 1:1 균등 분배
  remaining_weight = 1 - forced_assets_weight
else:
  remaining_weight = 1.0

# 그리디 선택 주식 비중 (점수 비례)
raw_weight[i] = final_asset_score[i]   (i in greedy_selected)
weight[i] = (raw_weight[i] / sum(raw_weight)) × remaining_weight   → 합 = remaining_weight

# 전체 비중 합 = forced_assets_weight + remaining_weight = 1


============================================================
5. BACKTEST
============================================================
선택된 포트폴리오의 과거 성과 시뮬레이션
[BACKTEST]

---------- 기간 구조 (룩어헤드 바이어스 방지) ----------
# 퀀트의 기본 원칙: 종목 선택에 사용한 데이터와 성과 평가 데이터는 반드시 분리

scoring_months = M (사용자 설정, 예: 24개월)
test_months    = N (사용자 설정, 예: 12개월)

스코어링 기간: [end - N - M, end - N]
  → 이 기간의 수익률·변동성·샤프 등으로 종목 점수 계산 및 선택

테스트 기간: [end - N, end]
  → 선택된 종목들의 실제 성과 평가 (순수 아웃오브샘플)

현재 추천: [end - M, end]
  → 최근 M개월로 스코어링 → 지금 당장 투자할 포트폴리오 추천

주의: M + N ≤ 60개월 (데이터 총 기간 한계)
      M이 데이터 시작일(2021-04-22)보다 이전이면 가용한 기간을 최대한 사용

---------- 설정 ----------
scoring_months (M): 스코어링 기간. 종목 점수 계산에 사용 (예: 24개월)
test_months (N):    테스트 기간. 아웃오브샘플 성과 평가에 사용 (예: 12개월)

구조:
  스코어링 기간: [end - N - M, end - N]  → 종목 선택 근거
  테스트 기간:  [end - N, end]            → 성과 평가 (데이터 누수 없음)
  현재 추천:    [end - M, end]            → 최근 M개월로 스코어링 후 현재 포폴 추천

권장 범위: scoring_months 12~36, test_months 6~24
  총 필요 데이터 = M + N ≤ 60개월 (데이터 수집 기간 한계)

# 하위 호환: backtest_months = test_months
  - 데이터 수집 기간: 2021-04-22 ~ 2026-04-22 (총 60개월)
  - backtest_months ≤ 30 권장: 스코어링/테스트 기간이 균등하게 분리됨
  - backtest_months > 30 시: 스코어링 기간이 데이터 시작일에 의해 단축될 수 있음
rebalance: 없음 (buy-and-hold, 단순화)
cost: 없음 (단순화)

---------- 프리셋 포트폴리오 계산 ----------
# 차트/테이블 비교를 위해 Aggressive·Balanced·Conservative 포트폴리오를 백그라운드 계산
# 사용자 포트폴리오와 동일 조건으로 실행:
#   - 동일 universe (동일 필터 적용)
#   - 동일 backtest_months 기간 (사용자 변경 시 즉시 반영)
#   - num_assets: 사용자 num_assets와 동일하게 사용
#   - forced_stocks + forced_assets: 사용자 선택 동일하게 적용
#   - forced_assets_weight: 사용자 값 동일하게 사용
#     (greedy 대상은 forced_stocks 제외, forced_assets는 원래부터 universe 밖)
#   - 각 프리셋 core 가중치로 score 계산 → Greedy 선택 → 백테스트

---------- 계산 ----------
portfolio_return_t = sum(weight[i] × r_t[i]   for i in selected)
cumulative_return  = cumprod(1 + portfolio_return_t) - 1

---------- 벤치마크 ----------
항상 SPY, 069500 둘 다 계산
차트(Chart 1, 4): 토글로 SPY / 069500 선택해서 표시 (기본: SPY)
테이블: SPY, 069500 둘 다 열로 표시 (혼합 여부 무관)


============================================================
6. CORE SKILLS OUTPUT
============================================================
백테스트 결과에서 최종 포트폴리오 지표 계산
[CORE_SKILLS_OUTPUT]

---------- 핵심 지표 — 테스트 기간 기준 (아웃오브샘플) ----------
# 모든 지표는 테스트 기간([end - N개월, end])의 포트폴리오 수익률로 계산
# 스코어링 기간 데이터와 완전 분리 → 데이터 누수 없음

returns:              cumulative_return_period(portfolio_return_t)   # 테스트 기간 누적 수익률
returns_annualized:   annualized_return(portfolio_return_t)          # 참고용 연환산
volatility:           annualized_volatility(portfolio_return_t)
sharpe_ratio:         (returns_annualized - rf) / volatility
alpha:                returns - beta × benchmark_cumret
  note: 테스트 기간 누적 수익률 기준 초과 성과 (표준 연환산 알파와 다름)
max_drawdown:         max_drawdown(cumulative_return)

---------- 추가 표시 지표 (인샘플 참고용) ----------
returns_scoring: 스코어링 기간의 동일 포트폴리오 누적 수익률
  → 테스트 수익률과 비교해 전략의 일관성 확인 가능
  → 인샘플 성과이므로 미래 예측에 사용 금지

---------- 보조 지표 (테이블 표시용, 점수 미반영) ----------
dividend_yield: sum(weight[i] × dividend_yield[i] for i in selected)
  note: 가중평균 배당수익률. 배당 미지급 자산은 0으로 처리

---------- Portfolio Score ----------
# 정규화 기준: 아래 6개 포트폴리오의 각 지표 min/max 기준으로 상대 정규화
# comparison_set = [user, aggressive, balanced, conservative, SPY, 069500]
# 가중치: 모든 포트폴리오(프리셋 포함)에 사용자 가중치(weight_*)를 동일 적용
#         → 동일 기준으로 비교해야 순위가 의미 있음

portfolio_score =
  weight_return  × normalized(returns,         ref=comparison_set)
+ weight_risk    × normalized_risk(volatility, ref=comparison_set)
+ weight_sharpe  × normalized(sharpe_ratio,    ref=comparison_set)
+ weight_alpha   × normalized(alpha,           ref=comparison_set)
+ weight_mdd     × normalized_risk(max_drawdown, ref=comparison_set)

# → 항상 0~1 보장. 점수 의미: 사용자 기준으로 6개 포트폴리오 중 상대적 위치


============================================================
7. STRATEGY PRESETS
============================================================
사용자가 직접 가중치를 설정하지 않아도 되는 기본 전략 템플릿
[STRATEGY_PRESETS]

# 두 가지 역할:
# 1. 사용자 초기값: 프리셋 버튼 선택 시 파라미터 자동 세팅 (이후 수정 가능)
# 2. 비교군 고정값: 차트/테이블의 비교 포트폴리오는 아래 값을 항상 고정 사용
#    → allow_kr, use_momentum, filters 등 모든 전략 파라미터 고정
#    → 기간(scoring_months, test_months)과 forced_assets만 사용자 값 공유
#    → 비교군이 사용자 설정에 영향받지 않아야 공정 비교 가능

---------- Aggressive ----------
weight_return:      10
weight_risk:        1
weight_sharpe:      3
weight_alpha:       5
weight_mdd:         1
num_assets:         6          # 비교군 고정값 — 소수 집중 투자
scoring_months:     24
test_months:        12
use_momentum:       true
momentum_direction: trend_following
momentum_window:    63
momentum_weight:    0.20
use_rsi_filter:     false
allow_us:           true
allow_kr:           false

---------- Balanced ----------
weight_return:      5
weight_risk:        4
weight_sharpe:      6
weight_alpha:       3
weight_mdd:         2
num_assets:         10         # 비교군 고정값 — 중간 분산
scoring_months:     24
test_months:        12
use_momentum:       false
use_rsi_filter:     false
allow_us:           true
allow_kr:           true

---------- Conservative ----------
weight_return:      2
weight_risk:        6
weight_sharpe:      4
weight_alpha:       1
weight_mdd:         7
num_assets:         15         # 비교군 고정값 — 넓은 분산
scoring_months:     24
test_months:        12
use_momentum:       false
use_rsi_filter:     true
rsi_upper_bound:    65
use_var_cvar_filter: true
var_max:            -0.02
cvar_max:           -0.04
allow_us:           true
allow_kr:           false

# 비교군 num_assets는 사용자 설정과 무관하게 고정
# → 전략 특성(집중/분산)이 비교에 반영됨


============================================================
8. VISUALIZATION
============================================================
대시보드에 표시할 차트 및 테이블 구성 규칙
[VISUALIZATION]

---------- Chart 1: 누적 수익률 그래프 ----------
type: line chart
x축: date (스코어링 + 테스트 기간 전체)
y축: cumulative_return (%)
경계선: 스코어링/테스트 기간 경계(test_start)에 빨간 점선 표시
series:
  - 사용자 포트폴리오 (user_portfolio) → 메인 색상     [항상 표시, 토글 불가]
  - SPY                                → 회색          [기본 on, 토글 가능]
  - 069500                             → 연회색        [기본 on, 토글 가능]
  - Aggressive 프리셋 포트폴리오        → 빨강          [기본 off, 토글 가능]
  - Balanced 프리셋 포트폴리오          → 초록          [기본 off, 토글 가능]
  - Conservative 프리셋 포트폴리오      → 파랑          [기본 off, 토글 가능]
토글 UI: 차트 상단 범례 클릭으로 on/off
표시 조건: 항상 표시

---------- Chart 2: 리스크-리턴 분포 ----------
type: scatter plot
x축: annualized_volatility — 테스트 기간 기준 (데이터 누수 없음)
y축: cumulative_return     — 테스트 기간 누적 수익률
점: 선택된 개별 자산의 테스트 기간 실제 성과
  - 포트폴리오 합산점은 크기를 크게 강조 표시 (★)
  - 자산군별 색상 구분 (stock/etf/bond)
표시 조건: 항상 표시

---------- Chart 3: 포트폴리오 비중 ----------
type: pie chart + bar chart 병렬
pie: 자산별 비중 (weight[i])
bar: 섹터별 합산 비중
  - 주식(stock): Assets.csv의 sector 컬럼 기준 (Technology, Financials 등)
  - ETF/채권: asset_type을 섹터 대신 사용 (etf, bond_proxy)
표시 조건: 항상 표시

---------- Chart 4: 드로우다운 차트 ----------
type: area chart (음수 영역)
x축: date
y축: drawdown (%) = (P_t - peak) / peak
series:
  - 사용자 포트폴리오 → 메인 색상   [항상 표시, 토글 불가]
  - SPY               → 회색        [기본 on, 토글 가능]
  - 069500            → 연회색      [기본 on, 토글 가능]
  - Aggressive        → 빨강        [기본 off, 토글 가능]
  - Balanced          → 초록        [기본 off, 토글 가능]
  - Conservative      → 파랑        [기본 off, 토글 가능]
토글 UI: 차트 상단 범례 클릭으로 on/off (Chart 1과 동일 방식)
표시 조건: 항상 표시

---------- Chart 5: 포트폴리오 Core Skills 레이더 ----------
type: radar chart
축: returns / volatility(역) / sharpe / alpha / mdd(역)
값: 선택된 전체 자산의 각 지표 가중평균 → 포트폴리오 하나의 다각형으로 표시
  portfolio_radar[지표] = sum(weight[i] × 지표[i] for i in selected)
  정규화: comparison_set(6개 포트폴리오) 기준 [0,1]
series:
  - 사용자 포트폴리오   [항상 표시]
  - Aggressive          [기본 off, 토글 가능]
  - Balanced            [기본 off, 토글 가능]
  - Conservative        [기본 off, 토글 가능]
표시 조건: 항상 표시

---------- Table: 지표 요약 ----------
columns:
  - 지표명
  - 사용자 포트폴리오 값
  - Aggressive 값
  - Balanced 값
  - Conservative 값
  - SPY (벤치마크)
  - 069500 (벤치마크)
rows:
  - Returns (연환산 수익률, %)
  - Volatility (연환산 변동성, %)
  - Sharpe Ratio
  - Alpha (%)
  - Max Drawdown (%)
  - Dividend Yield (%)       ← 보조 지표
  - Portfolio Score (0~1)   ← 사용자·프리셋만 표시. SPY·069500 열은 N/A
표시 조건: 항상 표시


============================================================
9. INSIGHT GENERATION
============================================================
포트폴리오 결과를 GPT API로 전송하여 자연어 인사이트 자동 생성
[INSIGHT_GENERATION]

---------- 방식 ----------
LLM: OpenAI GPT-4o
API 키: 서버 환경변수 OPENAI_API_KEY (배포 시 주입, 코드에 노출 금지)

---------- LLM에 전달할 데이터 ----------
portfolio_metrics:
  - strategy: 사용자 설정 전략명 (또는 "custom")
  - num_assets: 선택 종목 수
  - selected_assets: [{ticker, name, sector, asset_type, weight}]
  - returns: 연환산 수익률 (%)
  - volatility: 연환산 변동성 (%)
  - sharpe_ratio
  - alpha (%)
  - max_drawdown (%)
  - dividend_yield (%)
  - portfolio_score (0~1)
  - benchmark_returns: {SPY 수익률, 069500 수익률}
  - preset_comparison: {aggressive, balanced, conservative 각각의 returns/sharpe/mdd}
  - active_filters: 사용자가 켠 Advanced 필터 목록

---------- 시스템 프롬프트 ----------
"당신은 투자 포트폴리오 분석 전문가입니다.
아래 포트폴리오 데이터를 바탕으로 다음 규칙에 따라 인사이트를 생성하세요:
1. 핵심 성과 요약 1문장 (수익률, 리스크 중심)
2. 벤치마크 또는 프리셋 대비 특징 1문장
3. 개선 또는 주의사항 제안 1문장
- 전문 용어는 간단히 설명 병기
- 수치는 반드시 포함
- 한국어로 작성
- 총 3문장 이내"

---------- 출력 형식 ----------
- 대시보드 하단 인사이트 카드에 표시
- GPT 응답을 그대로 렌더링 (마크다운 지원)
- 로딩 중 스피너 표시
- API 오류 시 fallback: "인사이트를 불러올 수 없습니다."


============================================================
10. UI/UX
============================================================
대시보드 레이아웃, 입력 컨트롤, 인터랙션 흐름 명세
[UI_UX]

---------- 전체 레이아웃 ----------
2-column 구조 (데스크탑 기준):

  [Left Panel - 고정 사이드바]          [Main Area - 스크롤 가능]
  ┌─────────────────────────┐           ┌────────────────────────────┐
  │ Strategy Preset 버튼 그룹 │           │ Chart 1: 누적 수익률        │
  │ ─────────────────────── │           │ Chart 2: 리스크-리턴 분포   │
  │ Core Parameters          │           │ Chart 3: 포트폴리오 비중    │
  │  - 가중치 슬라이더 × 5   │           │ Chart 4: 드로우다운         │
  │  - num_assets 슬라이더   │           │ Chart 5: 레이더 차트        │
  │  - backtest_months 슬라이더│           │ Table:   지표 요약          │
  │ ─────────────────────── │           │ Insight Card               │
  │ [고급 설정 펼치기 ▼]     │           └────────────────────────────┘
  │  Advanced Parameters     │
  │  forced_stocks 검색      │
  │  forced_assets 선택      │
  └─────────────────────────┘

---------- 입력 컨트롤 명세 ----------

Strategy Preset:
  - 버튼 그룹: [Aggressive] [Balanced] [Conservative]
  - 선택 시 Left Panel 파라미터 자동 세팅
  - 이후 수동 수정 가능 → 선택된 프리셋 표시 해제 (Custom으로 전환)

Core Parameters:
  weight_return / weight_risk / weight_sharpe / weight_alpha / weight_mdd:
    - 슬라이더 0~10, 정수 (사용자는 상대적 중요도만 설정)
    - 슬라이더 조작 즉시 자동 정규화: weight[i] = value[i] / sum(values)
    - 실제 적용 비율을 슬라이더 옆에 % 형태로 실시간 표시
      예) 수익률 ●━━━━○ 5  →  33%
  num_assets:
    - 슬라이더 1~20, 정수
  scoring_months (M):
    - 슬라이더 6~36, 정수, 오른쪽에 "스코어링: 약 X년 Y개월" 표시
  test_months (N):
    - 슬라이더 3~36, 정수, 오른쪽에 "테스트: 약 X년 Y개월" 표시
    - 상한 자동 제한: min(36, 60 - scoring_months)
    - 합계 표시: "총 M+N개월 사용 / 보유 60개월"

Advanced Parameters (기본 접힘):
  use_* 토글 스위치:
    - 켜면 해당 파라미터 슬라이더/입력창 슬라이드 다운으로 나타남
  momentum_direction:
    - 드롭다운: [추세추종 (오르는 종목)] [역추세 (내린 종목)]
  rsi_upper_bound / pe_max / pb_max 등 수치 파라미터:
    - 슬라이더 + 오른쪽 숫자 입력창 (양방향 연동)
  allow_us / allow_kr:
    - 체크박스 2개, 둘 다 해제 시 빨간 경고 "최소 1개 선택 필요"
  forced_stocks (주식 수동 선택):
    - 검색창: ticker 또는 종목명 입력 → 실시간 필터링
    - 검색 결과 리스트: ticker | 종목명 | 섹터 | 시장(US/KR) 표시
    - 클릭으로 선택 → 선택된 종목 태그 형태로 표시 (× 버튼으로 제거)
    - 선택 가능 범위: universe(is_active stock) 내 종목만
  forced_assets (ETF/채권 수동 선택):
    - 채권 ETF / 상품 ETF / 지수 ETF 그룹별 체크박스 목록
    - 각 항목 옆 [?] 버튼 → 툴팁 (자산 설명)
  forced_assets_weight:
    - forced_stocks + forced_assets 중 하나라도 선택 시 자동 노출
    - 슬라이더 0~0.8
    - "강제 자산 N개 × 각 X% / 나머지 그리디 주식 Y%" 실시간 표시

[분석 실행] 버튼:
  - 파라미터 변경 후 명시적 실행 (자동 실행 아님)
  - 실행 중 로딩 스피너 + 진행 단계 텍스트
    ("종목 필터링 중... → 점수 계산 중... → 백테스트 실행 중...")
  - 오류 시 메시지 카드 표시

---------- 인터랙션 흐름 ----------
1. 페이지 진입 → Balanced 프리셋 기본값으로 자동 분석 실행
2. 파라미터 변경 → [분석 실행] 버튼 활성화 (변경 사항 있음 표시)
3. [분석 실행] 클릭 → 로딩 → 결과 업데이트 (모든 차트·테이블·인사이트)
4. 차트 범례 클릭 → 해당 시리즈 즉시 토글 (재계산 없음)
5. forced_stocks / forced_assets 변경 → [분석 실행] 버튼 활성화
6. 가중치 슬라이더 5개 모두 0 설정 시 → [분석 실행] 비활성화 + 에러 메시지
   "모든 중요도가 0입니다. 최소 1개 이상 설정해주세요."

---------- 색상 가이드 ----------
사용자 포트폴리오:  #2563EB (파란색 계열, 메인)
Aggressive:         #DC2626 (빨강)
Balanced:           #16A34A (초록)
Conservative:       #2563EB 보다 연한 파랑 → #60A5FA
SPY:                #6B7280 (회색)
069500:             #9CA3AF (연회색)
경고/오류:          #EF4444 (빨강)
배경:               #F8FAFC (연한 회색)

---------- 파라미터 툴팁 (? 아이콘 hover/클릭 시 표시) ----------
Streamlit help= 인자 또는 st.help() 팝오버로 구현

[Core Parameters]
num_assets: ❓
  "선택할 종목 수입니다.
   ↑ 늘리면: 더 많은 종목에 분산 → 리스크 감소, 수익률 평균화
   ↓ 줄이면: 집중 투자 → 리스크 증가, 고수익 가능성"

backtest_months: ❓
  "과거 몇 개월 데이터로 성과를 평가할지 설정합니다.
   ↑ 늘리면: 더 긴 기간 검증 → 안정적이지만 최근 트렌드 반영 적음
   ↓ 줄이면: 최근 성과 중심 평가 → 최신 시장 상황 반영"

weight_return: ❓
  "수익률을 얼마나 중요하게 볼지 설정합니다.
   ↑ 높이면: 과거 수익률 높은 종목 선호 → 공격적 포트폴리오
   ↓ 낮추면: 수익률보다 다른 지표 우선시"

weight_risk: ❓
  "변동성(리스크)을 얼마나 중요하게 볼지 설정합니다.
   ↑ 높이면: 가격이 안정적인 종목 선호 → 방어적 포트폴리오
   ↓ 낮추면: 변동성 높아도 감수"

weight_sharpe: ❓
  "샤프 비율 = 수익률 ÷ 변동성. 리스크 대비 효율을 의미합니다.
   ↑ 높이면: 같은 위험이면 더 높은 수익, 균형 잡힌 종목 선호
   ↓ 낮추면: 효율성보다 다른 지표 우선시"

weight_alpha: ❓
  "시장(S&P500, 코스피) 대비 초과 수익을 의미합니다.
   ↑ 높이면: 시장을 이긴 종목 선호 → 적극적 종목 발굴
   ↓ 낮추면: 시장 수익률과 비슷해도 괜찮음"

weight_mdd: ❓
  "최대 낙폭(MDD) = 고점 대비 최대로 떨어진 폭.
   ↑ 높이면: 폭락이 적었던 종목 선호 → 손실 방어 중시
   ↓ 낮추면: 일시적 폭락 감수 가능"

[Advanced Parameters]
momentum_window: ❓
  "모멘텀을 계산할 기간입니다.
   ↑ 늘리면: 장기 추세 반영 (6개월~1년 흐름)
   ↓ 줄이면: 단기 반응 (최근 1~2개월 흐름)"

rsi_upper_bound: ❓
  "RSI = 최근 오른 힘 vs 내린 힘의 비율 (0~100).
   70 이상 = 과매수 (너무 많이 올라 조정 가능성)
   이 값 초과 종목을 제외합니다.
   ↑ 높이면: 더 관대 → 많이 오른 종목도 허용
   ↓ 낮추면: 더 보수적 → 과열 종목 엄격히 제외"

pe_max: ❓
  "PER = 주가 ÷ 주당순이익. 낮을수록 저평가.
   이 값 초과 종목(고평가 주식)을 제외합니다.
   ↑ 높이면: 고평가 주식도 허용
   ↓ 낮추면: 저평가 주식만 선택"

pb_max: ❓
  "PBR = 주가 ÷ 주당순자산. 낮을수록 자산 대비 저평가.
   이 값 초과 종목을 제외합니다."

roe_min: ❓
  "ROE = 자기자본으로 얼마나 벌었는지. 높을수록 수익성 좋음.
   이 값 미만 종목(수익성 낮은 기업)을 제외합니다.
   ↑ 높이면: 수익성 높은 기업만 선택 → 더 엄격
   ↓ 낮추면: 수익성 낮은 기업도 허용"

de_max: ❓
  "D/E = 부채 ÷ 자기자본. 낮을수록 재무 안정적.
   이 값 초과 종목(과다 부채 기업)을 제외합니다."

var_max / cvar_max: ❓
  "VaR = 하루 최대 예상 손실 (95% 확률 기준).
   CVaR = 최악의 날들 평균 손실.
   이 값 초과 종목(꼬리 리스크 큰 종목)을 제외합니다."

beta_min / beta_max: ❓
  "베타 = 시장 대비 민감도.
   베타 1 = 시장과 동일하게 움직임
   베타 > 1 = 시장보다 더 크게 움직임 (공격적)
   베타 < 1 = 시장보다 덜 움직임 (방어적)
   원하는 민감도 범위를 설정합니다."

forced_assets_weight: ❓
  "수동으로 선택한 자산들에 할당할 전체 비중입니다.
   예) 0.3 → 선택 자산 합계 30%, 나머지 70%는 자동 선택 주식
   선택 자산이 여러 개면 균등 분배됩니다."

---------- 튜토리얼 ----------
위치: 대시보드 상단 헤더 우측 [? 사용법] 버튼
동작: 클릭 시 step-by-step 안내 박스가 순서대로 표시됨
      다시 클릭하면 종료. session_state로 단계 관리.

튜토리얼 단계:
  Step 1: [전략 선택]
    "먼저 투자 성향에 맞는 전략을 선택하세요.
     Aggressive(공격적) / Balanced(균형) / Conservative(안정적)"
  Step 2: [종목 수·기간 설정]
    "선택할 종목 수와 백테스트 기간을 설정하세요.
     종목 수가 많을수록 분산투자, 기간이 길수록 장기 성과를 평가합니다."
  Step 3: [분석 실행]
    "설정 완료 후 [분석 실행] 버튼을 눌러주세요.
     결과가 아래 차트와 테이블에 자동으로 표시됩니다."
  Step 4: [차트 확인]
    "누적 수익률 그래프에서 내 포트폴리오와 SPY·코스피를 비교해보세요.
     범례를 클릭하면 시리즈를 켜고 끌 수 있습니다."
  Step 5: [고급 설정]
    "왼쪽 [고급 설정 펼치기]를 열면 필터·모멘텀·헷징 자산을
     세밀하게 조절할 수 있습니다."

UI 처리:
  - 각 단계는 해당 컴포넌트 근처에 st.info() 박스로 표시
  - [다음 →] [← 이전] [닫기] 버튼으로 탐색
  - 마지막 단계에서 [시작하기] 버튼 → 튜토리얼 종료 + 분석 자동 실행

---------- 반응형 ----------
- 데스크탑(1280px+): 2-column 레이아웃
- 태블릿(768px~): Left Panel 상단 배치, Main Area 하단
- 모바일: 지원 최소화 (심사는 데스크탑 기준)


============================================================
11. TECH STACK
============================================================
구현에 사용할 기술 스택 명세
[TECH_STACK]

---------- 핵심 프레임워크 ----------
Streamlit (Python)
  - 별도 프론트엔드 코드 없이 Python만으로 대시보드 구현
  - 슬라이더·체크박스·버튼 등 UI 컴포넌트 내장
  - 배포: Streamlit Community Cloud (무료, GitHub 연동)

---------- 주요 라이브러리 ----------
데이터 처리:
  - pandas        → CSV 로드, 데이터프레임 연산
  - numpy         → 수치 계산 (정규화, 통계)

시각화:
  - plotly        → 인터랙티브 차트 (line, scatter, pie, bar, area, radar)
  - plotly.express → 빠른 차트 생성

포트폴리오 계산:
  - pandas        → 수익률·변동성·MDD 계산
  - numpy         → 상관계수, 백분위수 계산

인사이트 생성:
  - openai        → GPT-4o API 호출
  - python-dotenv → 환경변수(API 키) 관리

---------- 프로젝트 구조 ----------
Portfolio_maker/
  ├── app.py              ← Streamlit 메인 진입점
  ├── engine/
  │   ├── scoring.py      ← ASSET SCORING 로직
  │   ├── selection.py    ← ASSET SELECTION (Greedy) 로직
  │   ├── backtest.py     ← BACKTEST 로직
  │   └── metrics.py      ← CORE SKILLS OUTPUT 계산
  ├── components/
  │   ├── sidebar.py      ← Left Panel (파라미터 입력 UI)
  │   ├── charts.py       ← Chart 1~5 렌더링
  │   ├── table.py        ← 지표 요약 테이블
  │   └── insight.py      ← GPT 인사이트 카드
  ├── data/               ← Data_collector/data/final/ 에서 복사한 CSV
  │   ├── Prices.csv
  │   ├── Volume.csv
  │   ├── Fundamentals.csv
  │   ├── macro.csv
  │   ├── Assets.csv
  │   └── correlation_matrix.csv
  └── .streamlit/
      └── secrets.toml    ← OPENAI_API_KEY (로컬 개발용)

---------- 배포 ----------
플랫폼: Streamlit Community Cloud
방법:
  1. GitHub 저장소에 코드 push
  2. share.streamlit.io 에서 저장소 연결
  3. App settings → Secrets 에 아래 내용 입력:
     OPENAI_API_KEY = "sk-..."
  4. 배포 URL 자동 생성 (심사 URL로 제출)
비용: 무료

API 키 코드 접근법:
  import streamlit as st
  api_key = st.secrets["OPENAI_API_KEY"]


============================================================
12. CURRENT RECOMMENDATION
============================================================
백테스트 결과를 바탕으로 현재 시장 기준 포트폴리오 추천
[CURRENT_RECOMMENDATION]

---------- 목적 ----------
백테스트로 전략의 유효성을 검증한 후, 동일 규칙을 적용해
현재 시점 기준의 포트폴리오 구성을 추천합니다.

---------- 스코어링 기간 ----------
scoring_period: [end - scoring_months, end]   (최근 M개월 전체 사용)
  → 백테스트의 스코어링/테스트 분리 없음
  → 가장 최신 데이터로 현재 유망 종목 선택

---------- 출력 ----------
- 선택 종목 + 비중 (종목 카드)
- 자산별 비중 파이 차트
- 섹터별 비중 바 차트
- 성과 지표 없음 (미래를 알 수 없으므로)
- 기준 데이터 기간 및 기준일 표시
- "과거 성과는 미래를 보장하지 않습니다" 면책 문구

---------- 연동 ----------
scoring_months 슬라이더 변경 → 추천 스코어링 기간 자동 반영
동일 파라미터(가중치, 필터, forced_assets 등) 사용

