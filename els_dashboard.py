import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="Step-down ELS Simulation Analyzer", layout="wide")
st.title("🎲 삼성전자-현대차 스텝다운 ELS 종합 시뮬레이터 및 가치평가 모형")
st.caption("실전 금융상품설명서 기반 모형 | 2자산 Worst-of 구조 몬테카를로 시뮬레이션 | 파생상품 교육용 대시보드")

# --- [교육용 가이드] 상품 구조 파악하기 ---
with st.expander("📚 [강의 핵심 노트] 삼성전자·현대차 스텝다운 ELS 구조 및 평가 원리 알아보기", expanded=True):
    st.markdown("""
    본 프로그램은 실제 공모 ELS 간이투자설명서의 핵심 조건을 파이썬 금융공학 코드로 시뮬레이션하는 교육용 도구입니다.
    
    1. **Worst-of (최악 자산 기준) 구조**: 두 기초자산(삼성전자, 현대차) 중 **만기 평가일에 더 많이 하락한 자산의 수익률**을 기준으로 상환 여부와 원금 손실을 결정합니다.
    2. **스텝다운(Step-down) 조기상환**: 6개월마다 돌아오는 평가일에 두 자산의 가격이 모두 최초기준가격 대비 점진적으로 낮아지는 배리어(예: 90%-90%-85%-85%-80%-75%)를 충족하면, 약정된 연 수익률을 지급하고 계약이 조기 종료됩니다.
    3. **낙인 배리어 (Knock-In Barrier, KI)**: 투자 기간 중(일별 또는 시뮬레이션 경로 상) 어느 한 자산이라도 최초기준가의 **50% 미만**으로 하락한 적이 있는지 감시합니다. 만약 낙인을 터치하고 만기 시점까지 조기상환 배리어를 회복하지 못하면, **최종 만기 시점에 더 많이 폭락한 자산의 하락률만큼 원금 손실**이 고스란히 발생합니다.
    4. **몬테카를로 가치평가(Monte Carlo Pricing)**: 미래의 불확실한 두 주가 경로를 상관관계를 반영한 기하브라운운동(GBM)으로 수만 번 시뮬레이션한 뒤, 각 경로에서 발생하는 현금흐름을 무위험자산 이자율로 할인하여 이 상품의 **'이론적 적정 가치(Fair Value)'**를 도출합니다.
    """)

# --- 사이드바: 변수 제어 및 금융 환경 세팅 ---
with st.sidebar:
    st.header("🛠️ 금융 시뮬레이션 변수 설정")
    
    st.subheader("1. 거시경제 및 자산 변수")
    r = st.number_input("무위험 이자율 (연 기준)", min_value=0.0, max_value=0.15, value=0.035, step=0.005, help="현금흐름 할인 및 위험중립 확률과정에 사용되는 시장 무위험 금리입니다.")
    rho = st.slider("두 자산 간의 상관계수 (Correlation)", min_value=-1.0, max_value=1.0, value=0.40, step=0.05, help="삼성전자와 현대차가 같이 움직이는 성향입니다. 1에 가까울수록 동조화되며 Worst-of 리스크가 줄어듭니다.")
    
    st.markdown("---")
    st.subheader("2. 개별 자산 변수")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        vol1 = st.number_input("삼성전자 변동성", min_value=0.05, max_value=0.60, value=0.25, step=0.01, help="삼성전자의 연간 수익률 표준편차입니다.")
    with col_v2:
        vol2 = st.number_input("현대차 변동성", min_value=0.05, max_value=0.60, value=0.30, step=0.01, help="현대차의 연간 수익률 표준편차입니다.")
        
    st.markdown("---")
    st.subheader("3. ELS 상품 조건")
    coupon_annual = st.number_input("약정 조건 (연 수익률 %)", min_value=1.0, max_value=20.0, value=8.0, step=0.5) / 100.0
    ki_barrier = st.slider("낙인 배리어 (Knock-In, %)", min_value=30, max_value=70, value=50, step=5, help="원금 손실 위험이 활성화되는 한계선입니다. 보통 최초기준가의 50%로 설정됩니다.")
    
    st.markdown("---")
    st.subheader("4. 연산 정밀도")
    n_sim = st.selectbox("시뮬레이션 횟수 (Paths)", [1000, 5000, 10000], index=1, help="횟수가 많을수록 정밀해지며 연산 시간이 늘어납니다.")

# --- 2자산 종속적 주가 경로 생성 엔진 (Cholesky Decomposition & GBM) ---
@st.cache_data
def run_els_simulation(r, vol1, vol2, rho, coupon_annual, ki_barrier, n_sim):
    # 기본 고정 변수 세팅 (3년 만기, 6개월 단위 조기상환 평가 = 총 6시점)
    T = 3.0
    steps_per_year = 252  # 일간 감시 가정 (낙인 터치 여부 정밀 감시를 위함)
    total_steps = int(T * steps_per_year)
    dt = T / total_steps
    
    # 6개월 단위(평가 시점)의 인덱스 계산
    eval_months = [6, 12, 18, 24, 30, 36]
    eval_steps = [int((m/12) * steps_per_year) for m in eval_months]
    
    # 스텝다운 배리어 조건 정의 (설명서 구조 반영: 90-90-85-85-80-75)
    barriers = [0.90, 0.90, 0.85, 0.85, 0.80, 0.75]
    
    # 초기 자산 가격 (100pt 100% 가중치 표준화)
    S1_0 = 100.0
    S2_0 = 100.0
    
    # Cholesky 분해를 통한 상관관계 난수 생성
    cov_matrix = np.array([[1.0, rho], [rho, 1.0]])
    L = np.linalg.cholesky(cov_matrix)
    
    # 경로 저장을 위한 행렬 초기화 [시뮬레이션 수, 타임스텝 + 1]
    S1 = np.zeros((n_sim, total_steps + 1))
    S2 = np.zeros((n_sim, total_steps + 1))
    S1[:, 0] = S1_0
    S2[:, 0] = S2_0
    
    # 기하브라운운동(GBM) 시뮬레이션 루프
    for t in range(1, total_steps + 1):
        Z = np.random.normal(0, 1, (2, n_sim))
        # 상관관계 주입
        Z_corr = np.dot(L, Z)
        
        S1[:, t] = S1[:, t-1] * np.exp((r - 0.5 * vol1**2) * dt + vol1 * np.sqrt(dt) * Z_corr[0, :])
        S2[:, t] = S2[:, t-1] * np.exp((r - 0.5 * vol2**2) * dt + vol2 * np.sqrt(dt) * Z_corr[1, :])
        
    # --- 손익 평가 및 분류 캐싱 ---
    payoffs = np.zeros(n_sim)
    s_times = np.zeros(n_sim)  # 언제 상환되었는지 기록 (할인용)
    status_counts = {"1차 조기상환": 0, "2차 조기상환": 0, "3차 조기상환": 0, "4차 조기상환": 0, "5차 조기상환": 0, "만기상환 (수익)": 0, "만기상환 (원금보존)": 0, "만기 원금 손실": 0}
    
    for i in range(n_sim):
        path1 = S1[i, :]
        path2 = S2[i, :]
        
        # 투자 기간 중 낙인(KI) 배리어 터치 여부 체크
        # 최초 기준가 100 대비 설정된 퍼센티지(예: 50) 미만으로 내려간 적이 있는지 감시
        has_knock_in = np.any(path1 < ki_barrier) or np.any(path2 < ki_barrier)
        
        redeemed = False
        # 1~6차 상환 시점 확인
        for seq, step_idx in enumerate(eval_steps):
            s1_ratio = path1[step_idx] / S1_0
            s2_ratio = path2[step_idx] / S2_0
            current_barrier = barriers[seq]
            
            # Worst-of 구조: 두 자산 모두 배리어 이상이어야 함
            if s1_ratio >= current_barrier and s2_ratio >= current_barrier:
                t_eval = (seq + 1) * 0.5  # 상환 시점 (년 단위)
                # 누적 약정 수익 계산 (예: 연 8%이면 6개월마다 4%씩 누적 지급)
                payoffs[i] = 100.0 * (1.0 + coupon_annual * t_eval)
                s_times[i] = t_eval
                
                status_name = f"{seq+1}차 조기상환" if seq < 5 else "만기상환 (수익)"
                status_counts[status_name] += 1
                redeemed = True
                break
                
        # 만약 만기까지 조기상환되지 못한 경우의 최종 처리
        if not redeemed:
            s_times[i] = T
            final_s1_ratio = path1[-1] / S1_0
            final_s2_ratio = path2[-1] / S2_0
            worst_final_ratio = min(final_s1_ratio, final_s2_ratio)
            
            if not has_knock_in:
                # 낙인을 터치한 적이 없다면 만기 상환 배리어를 못 넘었어도 원금 100% 보장 (더미 쿠폰 없음 가정)
                payoffs[i] = 100.0
                status_counts["만기상환 (원금보존)"] += 1
            else:
                # 투자 기간 중 낙인을 터치한 적이 있다면 원금 손실 발생
                # 최종 만기 가치는 worst 자산의 하락률과 선형 동조화됨
                payoffs[i] = 100.0 * worst_final_ratio
                status_counts["만기 원금 손실"] += 1
                
    # 위험중립 할인 적용하여 현재가치 가치평가 산출
    discounted_payoffs = payoffs * np.exp(-r * s_times)
    fair_value = np.mean(discounted_payoffs)
    
    return fair_value, status_counts, S1[:10, :], S2[:10, :]  # 가시성을 위해 샘플 경로 10개만 차트용 반환

# 시뮬레이션 연산 트리거
fair_value, status_counts, sample_s1, sample_s2 = run_els_simulation(r, vol1, vol2, rho, coupon_annual, ki_barrier, n_sim)

# --- 메인 지표 레이아웃 출력 ---
st.subheader("📊 시뮬레이션 기반 계량적 가치평가 결과")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="🎯 ELS 이론적 적정 가격 (Fair Value)",
        value=f"{fair_value:.2f} %",
        delta=f"액면가(100%) 대비 {fair_value - 100.0:.2f}%",
        delta_color="normal" if fair_value >= 100 else "inverse",
        help="시뮬레이션된 모든 만기 현금흐름을 현재 무위험 금리로 할인한 기댓값입니다. 발행사 수수료 등을 감안하기 전의 순수 자산가치입니다."
    )

with col2:
    loss_prob = (status_counts["만기 원금 손실"] / n_sim) * 100
    st.metric(
        label="🔥 최종 원금 손실(Knock-In 익스포저) 발생 확률",
        value=f"{loss_prob:.2f} %", # ✨ 안전하게 실수형(.2f) 포맷으로 통일
        delta="위험 수준 주의" if loss_prob > 15 else "안정적 구간",
        delta_color="inverse" if loss_prob > 15 else "normal",
        help="만기 시점에 조기상환을 전혀 받지 못하고 투자기간 중 낙인 배리어를 깨서 최종 원금 손실 확정 상태로 종료된 시나리오의 비율입니다."
    )

with col3:
    early_prob = sum([v for k, v in status_counts.items() if "조기상환" in k or "수익" in k]) / n_sim * 100
    st.metric(
        label="💰 약정 연수익 조기 및 만기 상환 성공률",
        value=f"{early_prob:.2f} %",
        help="투자자가 원금 손실 없이 성공적으로 약정된 연 이자 수익을 수취하고 안전하게 퇴출될 확률입니다."
    )

st.markdown("---")

# --- 차트 레이아웃 분할 ---
c_left, c_right = st.columns([6, 4])

with c_left:
    st.subheader("📈 시뮬레이션 주가 시나리오 샘플 경로 (상위 10개선)")
    st.caption("Cholesky 상관관계 모형이 탑재된 기하브라운운동(GBM) 자산 시뮬레이션 시각화")
    
    fig = go.Figure()
    time_axis = np.linspace(0, 3, sample_s1.shape[1])
    
    # 샘플 경로 드로잉
    for idx in range(5):
        fig.add_trace(go.Scatter(x=time_axis, y=sample_s1[idx, :], mode='lines', name=f"삼성전자 경로 #{idx+1}", line=dict(width=1.5)))
        fig.add_trace(go.Scatter(x=time_axis, y=sample_s2[idx, :], mode='lines', name=f"현대차 경로 #{idx+1}", line=dict(width=1.5, dash='dash')))
        
    # 낙인 가이드 수평선 추가
    fig.add_hline(y=ki_barrier, line_width=2.5, line_color="red", line_dash="solid", annotation_text=f"위험구간 낙인 배리어 ({ki_barrier}%)", annotation_position="bottom left")
    # 6개월 조기상환 평가 기준선 매칭 수평선 추가
    fig.add_hline(y=90, line_width=1, line_color="black", line_dash="dot", annotation_text="1~2차 상환선 (90%)")
    fig.add_hline(y=75, line_width=1, line_color="black", line_dash="dot", annotation_text="6차 만기상환선 (75%)")

    fig.update_layout(
        xaxis_title="투자 기간 (년 단위, 0 ~ 3년)",
        yaxis_title="최초 기준가 대비 주가 수준 (%))",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=10, b=20),
        plot_bgcolor="white",
        height=450
    )
    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='LightGray')
    st.plotly_chart(fig, use_container_width=True)

with c_right:
    st.subheader("🎯 시나리오별 최종 정산 결과 분포")
    st.caption(f"총 {n_sim:,}번의 위험중립 시뮬레이션 경로 추적 원형 차트")
    
    labels = list(status_counts.keys())
    values = list(status_counts.values())
    
    # 테마에 어울리는 손익 컬러 시퀀스 지정
    colors = ['#1a73e8', '#34a853', '#4285f4', '#66aa00', '#b8bb00', '#fbbc05', '#ea4335', '#d93025']
    
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker=dict(colors=colors))])
    fig_pie.update_layout(
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=-0.2), # ✨ 'center'를 'middle'로 수정
    height=450
)
    st.plotly_chart(fig_pie, use_container_width=True)

# --- 📋 상세 시나리오 카운트 데이터 표 출력 ---
st.subheader("📋 시나리오별 통계 및 세부 항목 설명")
detailed_data = []
for k, v in status_counts.items():
    prob = (v / n_sim) * 100
    
    # 각 정산 케이스별 디테일 설명 매핑
    if "조기상환" in k:
        desc = f"발행 후 해당 시점(6~30개월) 평가일에 두 자산 주가가 모두 상환 기준 배리어 이상이 되어 원금과 연 {coupon_annual*100}%의 기간 경과 약정 수익을 받고 조기 종료된 안전한 케이스입니다."
    elif "수익" in k:
        desc = f"조기상환은 되지 않았으나 최종 3년 만기 평가일에 두 자산 모두 최종 만기 기준(75%) 이상에 위치하여, 3년치 전체 약정 이자({coupon_annual*3*100}%)를 모두 수취한 최상의 시나리오입니다."
    elif "원금보존" in k:
        desc = "만기 평가 배리어(75%)를 넘지는 못했으나, 전체 투자 기간 동안 두 자산 모두 낙인 배리어(50%)를 한 번도 하락 돌파(터치)한 적이 없으므로 계약 조건에 따라 투자 원금(100%)을 안전하게 보존받고 환급된 케이스입니다."
    else:
        desc = "투자 기간 중 한 자산이라도 낙인 배리어(50%)를 터치한 적이 있고, 만기 평가일에 최종 회복 기준(75%)을 넘지 못해 두 자산 중 더 많이 폭락한 자산의 하락률 그대로 손실률이 반영되어 원금 손실을 본 리스크 케이스입니다."
        
    detailed_data.append({"정산 시나리오 구분": k, "시나리오 발생 건수": f"{v:,} 건", "발생 확률 (Probability)": f"{prob:.2f} %", "시나리오별 상세 금융학적 설명": desc})

st.table(detailed_data)