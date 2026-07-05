import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 페이지 설정 ---
st.set_page_config(page_title="KOSPI 200 Futures Margin Call Simulator", layout="wide")
st.title("📉 코스피 200 선물 실시간 마진콜 시뮬레이터")
st.caption("선물 일일정산(Marking-to-Market) 메커니즘 및 역사적 쇼크 시나리오 시각화 도구")

# --- 1. 변동성 시나리오 정의 ---
SCENARIOS = {
    "변동성 박스권 (중간 마진콜 발생형)": [0.012, -0.035, -0.042, 0.015, -0.021, 0.038, 0.012, -0.005, 0.025, -0.008],
    "2008년 글로벌 금융위기 쇼크 (Bear Market)": [-0.025, -0.042, 0.015, -0.038, -0.051, 0.022, -0.045, -0.031, 0.011, -0.048],
    "2020년 코로나 팬데믹 쇼크 (Crash & Rebound)": [-0.038, -0.045, -0.057, 0.021, 0.048, -0.032, -0.029, 0.055, 0.031, -0.015],
    "숏 스퀴즈 폭등 장세 (Bull Market Shock)": [0.015, 0.032, 0.028, -0.005, 0.041, 0.025, -0.012, 0.038, 0.019, 0.022]
}

# --- 2. 사이드바 UI 컨트롤러 ---
with st.sidebar:
    st.header("⚙️ 선물 계약 및 증거금 설정")
    selected_scenario = st.selectbox("📅 시장 변동성 시나리오 선택:", list(SCENARIOS.keys()))
    
    st.markdown("---")
    st.subheader("📝 포지션 세부 설정")
    pos_type = st.selectbox("매매 방향 (Position):", ["매수 (Long)", "매도 (Short)"])
    init_index = st.number_input("진입 시점 코스피 200 지수", min_value=100.0, max_value=600.0, value=300.0, step=1.0)
    qty = st.number_input("계약 수량 (수량)", min_value=1, max_value=100, value=5, step=1)
    
    multiplier = 250000
    contract_value = init_index * multiplier * qty
    st.metric(label="📊 총 계약 금액 (Notional Value)", value=f"{contract_value:,.0f} 원")
    
    st.markdown("---")
    st.subheader("🛡️ 증거금률 설정 (%)")
    init_margin_rate = st.slider("개시증거금율 (Initial Margin %)", min_value=5.0, max_value=20.0, value=9.0, step=0.5) / 100
    maint_margin_rate = st.slider("유지증거금율 (Maintenance Margin %)", min_value=3.0, max_value=15.0, value=6.0, step=0.5) / 100

# --- 3. 마진콜 및 증거금 시뮬레이션 연산 엔진 ---
returns = SCENARIOS[selected_scenario]
index_path = [init_index]
for r in returns:
    index_path.append(index_path[-1] * (1 + r))

days = [f"진입시점 (Day 0)"] + [f"Day {i}" for i in range(1, 11)]

initial_margin_required = contract_value * init_margin_rate
maint_margin_required = contract_value * maint_margin_rate

df_list = []
current_equity = initial_margin_required 
total_accumulated_pnl = 0  

for day_idx, current_idx in enumerate(index_path):
    if day_idx == 0:
        pnl = 0
        pct_change = 0.0
        margin_call_triggered = "정상"
        add_margin_required = 0
    else:
        prev_idx = index_path[day_idx - 1]
        pct_change = (current_idx - prev_idx) / prev_idx * 100
        
        if pos_type == "매수 (Long)":
            pnl = (current_idx - prev_idx) * multiplier * qty
        else:
            pnl = (prev_idx - current_idx) * multiplier * qty
            
        total_accumulated_pnl += pnl
        current_equity += pnl
        
        if current_equity < maint_margin_required:
            margin_call_triggered = "🚨 마진콜 발생"
            add_margin_required = initial_margin_required - current_equity
            current_equity = initial_margin_required 
        else:
            margin_call_triggered = "정상"
            add_margin_required = 0

    excess_margin = max(0, current_equity - initial_margin_required)
    
    df_list.append({
        "영업일": days[day_idx],
        "KOSPI 200 지수": current_idx,
        "변동률(%)": pct_change,
        "일일손익 (원)": pnl,
        "예탁총액 (원)": current_equity,
        "개시증거금 (원)": initial_margin_required,
        "유지증거금 (원)": maint_margin_required,
        "초과증거금 (원)": excess_margin,
        "추가증거금 필요액 (원)": add_margin_required,
        "상태": margin_call_triggered
    })

df_res = pd.DataFrame(df_list)

# --- 4. 메인 대시보드 화면 시각화 ---
st.subheader(f"📊 선택된 시나리오 시각화 분석: `{selected_scenario}`")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    pnl_prefix = "+" if total_accumulated_pnl >= 0 else ""
    st.metric("💰 10 영업일 총손익 (Total P&L)", f"{pnl_prefix}{total_accumulated_pnl:,.0f} 원")
with col_m2:
    st.metric("🚨 마진콜 총 발생 횟수", f"{sum(df_res['상태'] == '🚨 마진콜 발생')} 회")
with col_m3:
    st.metric("🎯 개시 증거금 (기준액)", f"{initial_margin_required:,.0f} 원")
with col_m4:
    st.metric("🛡️ 유지 증거금 (보더라인)", f"{maint_margin_required:,.0f} 원")

# 인터랙티브 그래프 차트 생성
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_res["영업일"], y=df_res["예탁총액 (원)"], mode='lines+markers', name='💰 일별 예탁총액 (Account Equity)', line=dict(color='purple', width=3.5)))
fig.add_trace(go.Scatter(x=df_res["영업일"], y=df_res["초과증거금 (원)"], mode='lines', name='🟢 초과증거금 (Excess Margin)', line=dict(color='rgba(46, 204, 113, 0.8)', width=2, dash='dot')))

fig.add_hline(y=initial_margin_required, line_width=2, line_dash="dash", line_color="orange", 
              annotation_text="개시증거금 기준선", annotation_font=dict(color="black", size=12), annotation_position="top left")
fig.add_hline(y=maint_margin_required, line_width=2, line_dash="dash", line_color="red", 
              annotation_text="⚠️ 유지증거금 기준선 (마진콜 발생선)", annotation_font=dict(color="black", size=12), annotation_position="bottom left")

mc_days = df_res[df_res["상태"] == "🚨 마진콜 발생"]
if not mc_days.empty:
    fig.add_trace(go.Scatter(
        x=mc_days["영업일"], 
        y=[maint_margin_required] * len(mc_days), 
        mode='markers', 
        name='🚨 마진콜 발생 시점', 
        marker=dict(color='red', size=15, symbol='x')
    ))

fig.update_layout(
    xaxis_title="경과 영업일",
    yaxis_title="증거금 및 예탁금 규모 (원)",
    hovermode="x unified",
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, font=dict(color="black")),
    margin=dict(l=20, r=20, t=30, b=20),
    plot_bgcolor="white",
    height=550
)
fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray', tickfont=dict(color="black"))
fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray', tickfont=dict(color="black"))

st.plotly_chart(fig, use_container_width=True)

# --- 5. 일별 정산 데이터 원장 생성 ---
st.subheader("📋 일별 정산 및 증거금 변동 상세 내역서")

df_display = pd.DataFrame()
df_display["영업일"] = df_res["영업일"]

# 괄호 형태의 변동률 결합 문자열 생성
idx_strings = []
for idx, row in df_res.iterrows():
    val = row["KOSPI 200 지수"]
    chg = row["변동률(%)"]
    if row["영업일"] == "진입시점 (Day 0)":
        idx_strings.append(f"{val:,.2f}")
    elif chg >= 0:
        idx_strings.append(f"{val:,.2f} (+{chg:.2f}%)")
    else:
        idx_strings.append(f"{val:,.2f} ({chg:.2f}%)")

df_display["KOSPI 200 지수 (전일대비)"] = idx_strings

# 화폐 단위 숫자 포맷팅
for col in ["일일손익 (원)", "예탁총액 (원)", "개시증거금 (원)", "유지증거금 (원)", "초과증거금 (원)", "추가증거금 필요액 (원)"]:
    df_display[col] = df_res[col].apply(lambda x: f"{x:,.0f}" if x != 0 else "0")

df_display["상태"] = df_res["상태"]

# [가장 안전한 로우 스타일 지정 함수]
def style_rows(row):
    # 기본 스타일은 빈 문자열로 초기화
    styles = [''] * len(row)
    
    # 1. 지수 하락 시 (전일대비 컬럼에 마이너스 부호가 있으면) 해당 셀 텍스트를 빨간색(#FF0000)으로 설정
    if "-" in str(row["KOSPI 200 지수 (전일대비)"]):
        styles[1] = 'color: #FF0000; font-weight: bold;'
        
    # 2. 마진콜 발생 시 맨 오른쪽 상태 셀 배경과 글씨 강조
    if "🚨" in str(row["상태"]):
        styles[8] = 'background-color: #FDE8E8; color: #FF0000; font-weight: bold;'
        
    return styles

# 스타일이 적용된 데이터프레임 렌더링
st.dataframe(df_display.style.apply(style_rows, axis=1), use_container_width=True)