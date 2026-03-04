import streamlit as st
from mapping import COLUMNS

def get_display_labels():
    """
    화면 표시용 컬럼명 매핑 반환
    영문/기본 컬럼명을 사용자가 읽기 좋은 한글 라벨로 변환합니다.
    """
    qty_nm = COLUMNS['qty']
    amt_nm = COLUMNS['amt_krw']
    return {
        f"{qty_nm}_P": "계획수량",
        "단가_P": "계획단가(외화)",
        f"{amt_nm}_P": "계획금액(KRW)",
        f"{qty_nm}_A": "실적수량",
        "단가_A": "실적단가(외화)",
        f"{amt_nm}_A": "실적금액(KRW)",
        "총매출차이": "총차이(KRW)",
        "수량차이_Impact": "수량효과",
        "단가차이_Impact": "단가효과",
        "환율차이_Impact": "환율효과"
    }

def display_summary_metrics(df):
    """
    상단 대시보드 요약 지표 표시
    전체 합계를 계산하여 사용자에게 요약 리포트를 제공합니다.
    """
    if df.empty:
        return

    # 합계 계산
    total_diff = df['총매출차이'].sum()
    q_impact = df['수량차이_Impact'].sum()
    p_impact = df['단가차이_Impact'].sum()
    er_impact = df['환율차이_Impact'].sum()

    # 4컬럼 레이아웃 생성
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("📊 총 매출 차이", f"{total_diff:,.0f}원")
    m2.metric("📦 수량 효과", f"{q_impact:,.0f}원")
    m3.metric("💰 단가 효과", f"{p_impact:,.0f}원")
    m4.metric("💱 환율 효과", f"{er_impact:,.0f}원")
    
    st.divider()

def format_analysis_table(df):
    """
    데이터프레임에 스타일과 포맷 적용
    계획/실적 데이터 검증을 위해 가독성을 극대화합니다.
    """
    # 1. 표시용 라벨로 컬럼명 변경
    labels = get_display_labels()
    display_df = df.rename(columns=labels)

    # 2. 숫자 포맷 정의
    format_dict = {
        "계획수량": "{:,.0f}", "계획단가(외화)": "{:,.2f}", "계획금액(KRW)": "{:,.0f}",
        "실적수량": "{:,.0f}", "실적단가(외화)": "{:,.2f}", "실적금액(KRW)": "{:,.0f}",
        "총차이(KRW)": "{:,.0f}", "수량효과": "{:,.0f}", "단가효과": "{:,.0f}", "환율효과": "{:,.0f}"
    }

    # 3. 색상 로직 (임계값 기준 하이라이트)
    def color_variance(val):
        if isinstance(val, (int, float)):
            if val > 100:  # 양수 효과 (초록)
                return 'background-color: #d1e7dd; color: #0f5132; font-weight: bold;'
            if val < -100: # 음수 효과 (빨강)
                return 'background-color: #f8d7da; color: #842029; font-weight: bold;'
        return ''

    # 4. 스타일 적용 및 반환
    styled_df = display_df.style.format(format_dict).applymap(
        color_variance, 
        subset=["총차이(KRW)", "수량효과", "단가효과", "환율효과"]
    )
    
    return styled_df
