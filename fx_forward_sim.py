import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 페이지 설정 ---
st.set_page_config(page_title="FX Forward Theoretical Price Simulator", layout="wide")
st.title("💱 통화선물 이론가격 및 금리평가설(CIP) 시뮬레이터")
st.caption("한국은행(BOK) vs 미국 연준(Fed) 금리 스프레드에 따른 환율 및 투자 성과 동등화 과정 시각화")

# --- 1. 사이드바 UI 컨트롤러 ---
with st.sidebar:
    st.header("⚙️ 거시경제 변수 및 조건 설정")
    
    st.subheader("🏦 국가별 변동 금리 설정")
    r_kor = st.slider("한국은행 기준금리 (r_KOR, %)", min_value=0.0, max_value=10.0, value=3.5, step=0.1) / 100
    r_usd = st.slider("미국 연준 기준금리 (r_USD, %)", min_value=0.0, max_value=10.0, value=5.0, step=0.1) / 100
    
    st.markdown("---")
    st.subheader("💵 환율 및 기간 설정")
    spot_fx = st.number_input("현재 현물환율 (Spot FX, 원/달러)", min_value=500.0, max_value=2000.0, value=1350.0, step=5.0)
    
    months = st.selectbox("투자 및 만기 기간 선택", [3, 6, 9, 12], index=3)
    T = months / 12

    st.markdown("---")
    st.subheader("💰 시뮬레이션 가상 자금")
    principal_usd = st.number_input("기준 투자 자금 ($)", min_value=1000, max_value=1000000, value=10000, step=1000)

# --- 2. 수학적 연산 엔진 ---
rate_spread = r_kor - r_usd
forward_fx = spot_fx * (1 + r_kor * T) / (1 + r_usd * T)

final_usd = principal_usd * (1 + r_usd * T)
final_usd_to_kor = final_usd * forward_fx  

principal_kor = principal_usd * spot_fx
final_kor = principal_kor * (1 + r_kor * T)

# --- 3. 메인 대시보드 화면 지표 출력 ---
st.subheader("📊 주요 산출 지표 결과 원장")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📉 금리 스프레드 (한 - 미)", f"{rate_spread*100:+.2f} %p")
with col2:
    st.metric("🔍 현재 현물환율 (Spot)", f"{spot_fx:,.2f} 원")
with col3:
    st.metric("🎯 통화선물 이론가격 (Forward)", f"{forward_fx:,.2f} 원")
with col4:
    st.metric("💎 스왑포인트 (Forward - Spot)", f"{forward_fx - spot_fx:+.2f} 원")

st.markdown("---")

# --- 4. 수정된 무차익거래 3단계 과정 레이어 ---
st.subheader("💡 무차익거래 조건에 따른 성과 동등화(Parity) 3단계 과정")

with st.expander("1단계: 금리 차이에 따른 자금의 만기 가치 분기 (환율 미적용 상태)", expanded=True):
    st.markdown(f"""
    원금 {principal_usd:,.0f} 달러를 가지고 각국 금리로 만기({months}개월)까지 투자했을 때의 순수 만기 금액 계산 과정입니다.
    
    - **미국에 투자 시 (달러 기준):** \${principal_usd:,.0f} × [1 + ({r_usd*100:.1f}% × {months}/12)] = **\${final_usd:,.2f}**
    - **한국에 투자 시 (초기 원화 환전 상태):** ₩{principal_kor:,.0f} × [1 + ({r_kor*100:.1f}% × {months}/12)] = **₩{final_kor:,.0f}**
    """)

with st.expander("2단계: 환율 적용 시 발생하는 성과 불균형 감지", expanded=False):
    st.markdown(f"""
    만약 만기 시점에도 환율이 현재 현물환율({spot_fx:,.2f}원)과 똑같이 고정된다고 가정하면, 미국 투자 결과인 ${final_usd:,.2f}를 원화로 바꿨을 때 ₩{final_usd * spot_fx:,.0f}이 됩니다.
    
    이 금액은 한국에 투자해 얻은 확정 금액인 ₩{final_kor:,.0f}과 달라지므로, 글로벌 자금 시장에서 어느 한쪽으로 쏠리는 일방적인 차익거래 기회가 생기게 됩니다. 이러한 불균형을 해결하기 위해 선물환 시장에서 통화선물 가격의 조정이 일어납니다.
    """)

with st.expander("3단계: 최종 동등화 결론 (선물환 가격 조정 완료)", expanded=False):
    st.markdown(f"""
    따라서 무차익 원리에 의해 산출되는 시장의 균형 통화선물가격은 **{forward_fx:,.2f} 원**이 됩니다.
    
    - **[경로 A] 미국 투자 후 선물환 헤지:** 만기 달러 수령액(${final_usd:,.2f})을 정해둔 이론 선물환율({forward_fx:,.2f}원)로 환전 → **₩{final_usd_to_kor:,.0f}**
    - **[경로 B] 초기 환전 후 한국 투자:** 처음 원화로 환전한 금액을 한국 금리로 굴려 만기에 수령 → **₩{final_kor:,.0f}**
    
    선물환 계약을 통해 환위험을 제거하면, [경로 A]와 [경로 B]의 기대 성과가 **₩{final_kor:,.0f}로 정확하게 일치**하게 되며 시장은 균형 상태를 유지합니다.
    """)

st.markdown("---")

# --- 5. 시각화 그래프 및 가독성 설명 레이어 ---
st.subheader("📈 만기 시점 무위험 투자 성과 비교 차트 (원화 환산 기준)")

fig = go.Figure()

# 경로 A (미국 투자) 선 및 마커
fig.add_trace(go.Scatter(
    x=['0. 초기 투자 시점 (원화 기준)', '1. 만기 회수 시점 (원화 환산)'],
    y=[principal_kor, final_usd_to_kor],
    mode='lines+markers+text',
    name='[경로 A] 미국 투자 후 선물환 헤지',
    line=dict(color='#2980b9', width=3),
    marker=dict(size=12, symbol='circle'),
    text=[f"₩{principal_kor:,.0f}", f"₩{final_usd_to_kor:,.0f}"],
    textposition=["top left", "top center"],
    textfont=dict(color="black", size=12)
))

# 경로 B (한국 투자) 선 및 마커
fig.add_trace(go.Scatter(
    x=['0. 초기 투자 시점 (원화 기준)', '1. 만기 회수 시점 (원화 환산)'],
    y=[principal_kor, final_kor],
    mode='lines+markers+text',
    name='[경로 B] 초기 환전 후 한국 예치 투자',
    line=dict(color='#e67e22', width=3, dash='dash'),
    marker=dict(size=12, symbol='square'),
    text=["", f"₩{final_kor:,.0f}"],
    textposition="bottom center",
    textfont=dict(color="black", size=12)
))

# 최종 만기 균형 성과선 (Parity Target)
fig.add_hline(
    y=final_kor, line_width=1.5, line_dash="dot", line_color="red",
    annotation_text="🎯 무차익 균형 성과선 (Parity Level)", 
    annotation_font=dict(color="red", size=12), 
    annotation_position="bottom right"
)

fig.update_layout(
    yaxis=dict(
        title="자금 가치 (원화 환산, ₩)", 
        tickfont=dict(color="black"),
        range=[principal_kor * 0.98, max(final_kor, final_usd_to_kor) * 1.02],
        tickformat=",d"
    ),
    xaxis=dict(tickfont=dict(color="black", size=13)),
    plot_bgcolor="#F8F9FA",
    height=450,
    margin=dict(l=50, r=50, t=30, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray')
fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray')

st.plotly_chart(fig, use_container_width=True)

# 차트 직관성 보완을 위한 상세 설명 텍스트
st.info(f"""
**💡 차트 직관적으로 이해하기 (핵심 요약)**
* **출발점은 동일합니다:** 동일한 가치의 자금(₩{principal_kor:,.0f})을 들고 투자를 시작합니다.
* **불균형과 선물환율의 역할:** 미국 금리가 한국보다 높기 때문에 그대로 두면 미국 투자가 무조건 유리해야 하지만, 만기 환전 시 '이론 가격으로 조정된 통화선물환율({forward_fx:,.2f}원)'이 일종의 '패널티 환율'로 작용하게 됩니다.
* **균형(Parity):** 결국 두 투자 경로는 만기 시점에 '정확히 동일한 자금 규모(₩{final_kor:,.0f})'로 수렴하게 되며, 외환 및 금리 시장에서 무위험 차익거래 기회가 완벽하게 소멸함을 확인할 수 있음.
""")