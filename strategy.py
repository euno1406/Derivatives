import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 페이지 기본 설정 및 호환성 처리 ---
st.set_page_config(page_title="Option Strategy Analyzer", layout="wide")
st.title("📊 구조화 옵션 투자 전략 분석기 (Option Strategy Analyzer)")
st.caption("34가지 고급 전략 프리셋 완벽 작동 | 만기 Payoff vs Profit 동시 비교 | 개별 레그선 시각화")

# 구버전 패키지 환경과의 하위 호환성 확보
if not hasattr(st, "accordion"):
    class LegacyAccordion:
        def __init__(self, label, expanded=True): self.label = label
        def __enter__(self): st.markdown(f"### 📑 {self.label}"); return st.container().__enter__()
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    st.accordion = LegacyAccordion

# --- 1. 전략별 프리셋 정의 (34종 모든 괄호 구조 정밀 교정 완료) ---
STRATEGY_PRESETS = {
    # --- [기본 및 헤지 전략] ---
    "Naked Call": {
        "desc": "콜옵션 1개를 순수하게 매수(Long)하는 기본 포지션입니다.",
        "legs": [{"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1}]
    },
    "Naked Put": {
        "desc": "풋옵션 1개를 순수하게 매수(Long)하는 기본 포지션입니다.",
        "legs": [{"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1}]
    },
    "Covered Call": {
        "desc": "기초자산 주식 매수(Stock Long 1개) + 콜옵션 매도(Call Short 1개) 조합입니다.",
        "legs": [
            {"asset_type": "Stock", "position_type": "Long", "strike": 100, "premium": 0, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 5, "qty": 1}
        ]
    },
    "Protective Put": {
        "desc": "기초자산 주식 매수(Stock Long 1개) + 풋옵션 매수(Put Long 1개)로 하방 위험을 방어하는 전략입니다.",
        "legs": [
            {"asset_type": "Stock", "position_type": "Long", "strike": 100, "premium": 0, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1}
        ]
    },
    # --- [강세 및 약세 스프레드] ---
    "Bull Call Spread": {
        "desc": "낮은 행사가 콜 매수(Call Long 1개) + 높은 행사가 콜 매도(Call Short 1개) 조합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 90, "premium": 8, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 110, "premium": 2, "qty": 1}
        ]
    },
    "Bear Call Spread": {
        "desc": "낮은 행사가 콜 매도(Call Short 1개) + 높은 행사가 콜 매수(Call Long 1개) 조합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Short", "strike": 90, "premium": 8, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 110, "premium": 2, "qty": 1}
        ]
    },
    "Bull Put Spread": {
        "desc": "낮은 행사가 풋 매수(Put Long 1개) + 높은 행사가 풋 매도(Put Short 1개) 조합입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 90, "premium": 2, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 110, "premium": 8, "qty": 1}
        ]
    },
    "Bear Put Spread": {
        "desc": "낮은 행사가 풋 매도(Put Short 1개) + 높은 행사가 풋 매수(Put Long 1개) 조합입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Short", "strike": 90, "premium": 2, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 110, "premium": 8, "qty": 1}
        ]
    },
    # --- [날개형 시장중립 전략] ---
    "Butterfly": {
        "desc": "양 끝 행사가 콜 매수(각 1개) + 중간 행사가 콜 매도(Call Short 2개) 조합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 90, "premium": 10, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 5, "qty": 2},
            {"asset_type": "Call", "position_type": "Long", "strike": 110, "premium": 2, "qty": 1}
        ]
    },
    "Iron Butterfly": {
        "desc": "풋 매수(1개) + 풋 매도(1개) + 콜 매도(1개) + 콜 매수(1개) 조합입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 90, "premium": 2, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 6, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 110, "premium": 2, "qty": 1}
        ]
    },
    "Condor": {
        "desc": "행사가가 서로 다른 콜옵션 4개를 양 끝 매수(각 1개) + 안쪽 매도(각 1개) 조합한 형태입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 80, "premium": 12, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 95, "premium": 6, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 105, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 120, "premium": 1, "qty": 1}
        ]
    },
    "Iron Condor": {
        "desc": "외가격 풋 매수(1개) + 내가격 풋 매도(1개) + 내가격 콜 매도(1개) + 외가격 콜 매수(1개) 조합입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 80, "premium": 1, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 90, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 110, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 120, "premium": 1, "qty": 1}
        ]
    },
    # --- [기간 및 교차 스프레드] ---
    "Calendar Spread": {
        "desc": "행사가격은 같으나 만기가 다른 옵션 조합입니다 (근월물 Short 1개 + 원월물 Long 1개 가정).",
        "legs": [
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 3, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 7, "qty": 1}
        ]
    },
    "Diagonal Spread": {
        "desc": "행사가격과 만기일이 모두 다른 교차 스프레드 조합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Short", "strike": 105, "premium": 2, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 6, "qty": 1}
        ]
    },
    # --- [변동성 돌파 전략] ---
    "Straddle": {
        "desc": "행사가가 동일한 콜옵션 매수(Call Long 1개) + 풋옵션 매수(Put Long 1개) 동시 결합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 4, "qty": 1}
        ]
    },
    "Strangle": {
        "desc": "행사가가 서로 다른 외가격 풋옵션 매수(Put Long 1개) + 외가격 콜옵션 매수(Call Long 1개) 조합입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 90, "premium": 3, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 110, "premium": 3, "qty": 1}
        ]
    },
    "Strip": {
        "desc": "하방 변동성 확대에 무게를 둔 조합으로, 콜옵션 매수(1개) + 풋옵션 매수(Put Long 2개) 조합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 4, "qty": 2}
        ]
    },
    "Strap": {
        "desc": "상방 변동성 확대에 무게를 둔 조합으로, 콜옵션 매수(Call Long 2개) + 풋옵션 매수(1개) 조합입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 2},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 4, "qty": 1}
        ]
    },
    "Synthetic Futures": {
        "desc": "동일 행사가의 콜옵션 매수(Call Long 1개) + 풋옵션 매도(Put Short 1개)로 선물 매수 효과를 복제합니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 100, "premium": 5, "qty": 1}
        ]
    },
    # --- [크리스마스 트리형 스프레드] ---
    "Christmas Tree Call": {
        "desc": "비대칭형 콜 나비 스프레드로 완만한 상승 시 마진 극대화를 추구합니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 90, "premium": 10, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 105, "premium": 2, "qty": 1}
        ]
    },
    "Christmas Tree Put": {
        "desc": "비대칭형 풋 나비 스프레드로 완만한 하락세 요인에 베팅하며 상방 위험을 고정합니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 110, "premium": 10, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 100, "premium": 4, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 95, "premium": 2, "qty": 1}
        ]
    },
    # --- [비율 및 혼합 대칭형 전략] ---
    "Call Ratio Spread": {
        "desc": "매수 수량보다 외가격 매도 수량을 더 많이 배치하여 박스권 상단 마진을 노립니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 95, "premium": 7, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 110, "premium": 2, "qty": 2}
        ]
    },
    "Put Ratio Spread": {
        "desc": "외가격 풋 매도를 대량 설정하여 수익 구간을 넓히나 폭락 시 위험성이 존재합니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 105, "premium": 7, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 90, "premium": 2, "qty": 2}
        ]
    },
    "Collar": {
        "desc": "기초 주식 보유 상태에서 하방은 풋옵션 매수로 닫고 상방은 콜옵션 매도로 제어합니다.",
        "legs": [
            {"asset_type": "Stock", "position_type": "Long", "strike": 100, "premium": 0, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 90, "premium": 3, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 110, "premium": 3, "qty": 1}
        ]
    },
    "Seagull Spread": {
        "desc": "외가격 풋 매도를 일으켜 등가격 콜 스프레드의 비용 부담을 대폭 상쇄하는 구조화 전략입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Short", "strike": 85, "premium": 2, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 115, "premium": 1.5, "qty": 1}
        ]
    },
    # --- [고급 변동성 헤지 및 차익거래 포지션] ---
    "Reverse Butterfly": {
        "desc": "주가가 정체되면 손실을 보나 양방향으로 추세가 터질 때 이익을 얻는 날개 포지션입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Short", "strike": 90, "premium": 10, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 2},
            {"asset_type": "Call", "position_type": "Short", "strike": 110, "premium": 2, "qty": 1}
        ]
    },
    "Albatross Spread": {
        "desc": "콘도르보다 외가격 날개 간격을 대폭 확장시켜 광범위한 박스권 시간가치를 수취합니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 70, "premium": 18, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 95, "premium": 6, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 105, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 130, "premium": 0.5, "qty": 1}
        ]
    },
    "Ratio Straddle": {
        "desc": "행사가가 동일한 옵션들 중 특정 방향성 꼬리 리스크 방어를 위해 수량을 조정한 변동성 포지션입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 4, "qty": 2}
        ]
    },
    "Ratio Strangle": {
        "desc": "외가격 양 끝 행사가를 매수하되, 외가격 리스크 스큐에 연동되도록 매칭한 수량 배정법입니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Long", "strike": 90, "premium": 3, "qty": 2},
            {"asset_type": "Call", "position_type": "Long", "strike": 110, "premium": 3, "qty": 1}
        ]
    },
    "Inverse Iron Condor": {
        "desc": "아이언 콘도르 매도 포지션을 반대로 취해 횡보 구간 이탈 시 정액 확정 이익을 확보합니다.",
        "legs": [
            {"asset_type": "Put", "position_type": "Short", "strike": 80, "premium": 1, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 90, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 110, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 120, "premium": 1, "qty": 1}
        ]
    },
    "Synthetic Short Futures": {
        "desc": "콜 매도와 풋 매수를 대칭 결합하여 주가 하락 시 선형 이익이 발생하는 공매도 포지션을 복제합니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 5, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 5, "qty": 1}
        ]
    },
    "Box Spread": {
        "desc": "강세 콜 스프레드와 약세 풋 스프레드를 합성하여 만기 가치를 완전 고정하는 차익거래 모형입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 90, "premium": 12, "qty": 1},
            {"asset_type": "Call", "position_type": "Short", "strike": 110, "premium": 3, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 110, "premium": 11, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 90, "premium": 2, "qty": 1}
        ]
    },
    "Jelly Roll": {
        "desc": "동일 행사가의 타임 스프레드 왜곡 현상과 내재 무위험 금리 차이를 매칭하는 교차 만기형 스프레드입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Short", "strike": 100, "premium": 3, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 100, "premium": 4, "qty": 1},
            {"asset_type": "Call", "position_type": "Long", "strike": 100, "premium": 7, "qty": 1},
            {"asset_type": "Put", "position_type": "Short", "strike": 100, "premium": 2, "qty": 1}
        ]
    },
    "Guts": {
        "desc": "내가격(ITM) 콜옵션과 내가격 풋옵션을 동시에 매입하여 확실한 만기 내재 가치를 보장받는 변동성 배팅입니다.",
        "legs": [
            {"asset_type": "Call", "position_type": "Long", "strike": 90, "premium": 12, "qty": 1},
            {"asset_type": "Put", "position_type": "Long", "strike": 110, "premium": 12, "qty": 1}
        ]
    }
}

# --- 2. 개별 및 종합 손익(P&L) 연산 함수 ---
def get_component_curves(S_T, asset, position, strike, premium, qty):
    if asset == "Stock":
        payoff = (S_T - strike) if position == "Long" else (strike - S_T)
        profit = payoff
    elif asset == "Call":
        payoff = np.maximum(S_T - strike, 0) if position == "Long" else -np.maximum(S_T - strike, 0)
        profit = payoff - premium if position == "Long" else payoff + premium
    elif asset == "Put":
        payoff = np.maximum(strike - S_T, 0) if position == "Long" else -np.maximum(strike - S_T, 0)
        profit = payoff - premium if position == "Long" else payoff + premium
    return payoff * qty, profit * qty

# --- 3. 사이드바 제어 및 동적 레이아웃 ---
with st.sidebar:
    st.header("🛠️ 전략 및 포지션 세팅")
    
    if "prev_template" not in st.session_state:
        st.session_state.prev_template = "직접 구성 (Custom)"
    if "num_legs" not in st.session_state:
        st.session_state.num_legs = 1

    selected_template = st.selectbox("34가지 고급 전략 템플릿 로드:", ["직접 구성 (Custom)"] + list(STRATEGY_PRESETS.keys()))
    
    if selected_template != st.session_state.prev_template:
        st.session_state.prev_template = selected_template
        if selected_template != "직접 구성 (Custom)":
            st.session_state.num_legs = len(STRATEGY_PRESETS[selected_template]["legs"])
        else:
            st.session_state.num_legs = 1
        st.rerun()

    st.markdown("---")
    st.subheader("개별 포지션(Leg) 세부 조정")
    
    current_positions = []
    preset_legs = STRATEGY_PRESETS[selected_template]["legs"] if selected_template != "직접 구성 (Custom)" else []
    
    for i in range(st.session_state.num_legs):
        st.markdown(f"**📍 Position Leg #{i+1}**")
        
        defaults = {"asset": "Call", "pos": "Long", "strike": 100, "premium": 5.0, "qty": 1}
        if selected_template != "직접 구성 (Custom)" and i < len(preset_legs):
            p_leg = preset_legs[i]
            defaults = {"asset": p_leg["asset_type"], "pos": p_leg["position_type"], "strike": p_leg["strike"], "premium": float(p_leg["premium"]), "qty": int(p_leg["qty"])}
            
        col1, col2 = st.columns(2)
        with col1:
            asset = st.selectbox("자산 구분", ["Stock", "Call", "Put"], key=f"asset_{i}", index=["Stock", "Call", "Put"].index(defaults["asset"]))
            pos = st.selectbox("매매 방향", ["Long", "Short"], key=f"pos_{i}", index=["Long", "Short"].index(defaults["pos"]))
        with col2:
            strike_label = "매입가 (S)" if asset == "Stock" else "행사가 (K)"
            strike = st.number_input(strike_label, min_value=1, max_value=500, value=defaults["strike"], key=f"strike_{i}")
            prem = st.number_input("프리미엄", min_value=0.0, max_value=100.0, value=defaults["premium"] if asset != "Stock" else 0.0, step=0.5, key=f"prem_{i}") if asset != "Stock" else 0.0
            qty = st.number_input("수량", min_value=1, max_value=10, value=defaults["qty"], key=f"qty_{i}")
            
        current_positions.append({"leg_index": i+1, "asset_type": asset, "position_type": pos, "strike": strike, "premium": prem, "qty": qty})
        st.markdown("---")
        
    if selected_template == "직접 구성 (Custom)":
        if st.button("➕ 포지션 레그 추가"):
            st.session_state.num_legs += 1
            st.rerun()
        if st.session_state.num_legs > 1 and st.button("➖ 최근 포지션 삭제"):
            st.session_state.num_legs -= 1
            st.rerun()

# --- 4. 메인 분석 대시보드 시각화 엔진 ---
if selected_template != "직접 구성 (Custom)":
    st.info(f"📋 **전략 가이드 메세지 ({selected_template}):** {STRATEGY_PRESETS[selected_template]['desc']}")
else:
    st.warning("⚡ **자유 구성 모드:** 우측 사이드바에서 개별 레그를 추가하여 고유 구조화 파생 상품의 시뮬레이션을 생성할 수 있습니다.")

all_strikes = [p["strike"] for p in current_positions if p["strike"] > 0]
min_s = max(0, min(all_strikes) - 60) if all_strikes else 0
max_s = max(all_strikes) + 60 if all_strikes else 200
S_T = np.linspace(min_s, max_s, 600)

total_payoff = np.zeros_like(S_T)
total_profit = np.zeros_like(S_T)

fig = go.Figure()

for pos in current_positions:
    leg_payoff, leg_profit = get_component_curves(S_T, pos["asset_type"], pos["position_type"], pos["strike"], pos["premium"], pos["qty"])
    total_payoff += leg_payoff
    total_profit += leg_profit
    
    leg_name = f"Leg #{pos['leg_index']} [{pos['position_type']} {pos['asset_type']}]"
    fig.add_trace(go.Scatter(x=S_T, y=leg_payoff, mode='lines', name=leg_name, line=dict(width=1.5, dash='dot'), opacity=0.5))

fig.add_trace(go.Scatter(x=S_T, y=total_payoff, mode='lines', name='🎯 Total Payoff (결합 만기가치)', line=dict(dash='dash', color='gray', width=2.5)))
fig.add_trace(go.Scatter(x=S_T, y=total_profit, mode='lines', name='🔥 Total Profit (결합 순손익)', line=dict(color='red', width=4)))

for k in set(all_strikes):
    fig.add_vline(x=k, line_width=1, line_dash="dashdot", line_color="blue", opacity=0.4)

fig.update_layout(
    xaxis_title="만기 시점 기초자산 가격 (S_T)",
    yaxis_title="손익 (P&L)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=20, b=20),
    plot_bgcolor="white",
    height=650
)
fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray', zeroline=True, zerolinewidth=1.5, zerolinecolor='black')
fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray', zeroline=True, zerolinewidth=1.5, zerolinecolor='black')

st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 포트폴리오 자산 명세서")
# [오류 해결] 렌더링 스타일 인덱스 예외(IndexError)를 발생시키는 st.table 대신 대용량 데이터 전용 st.dataframe 인터페이스로 교체
st.dataframe(current_positions, use_container_width=True)