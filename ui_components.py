import streamlit as st
import pandas as pd
from mapping import COLUMNS

def get_display_labels():
    """화면 표시용 컬럼명 매핑 반환"""
    qty_nm = COLUMNS['qty']
    amt_nm = COLUMNS['amt_krw']
    return {
        f"{qty_nm}_P": "계획수량", 
        "단가_P": "계획단가", 
        f"{amt_nm}_P": "계획금액",
        f"{qty_nm}_A": "실적수량", 
        "단가_A": "실적단가", 
        f"{amt_nm}_A": "실적금액",
        "총매출차이": "총차이(KRW)", 
        "수량차이_Impact": "수량효과", 
        "단가차이_Impact": "단가효과", 
        "환율차이_Impact": "환율효과"
    }

def display_summary_metrics(df):
    """상단 요약 지표 (데이터 타입 검증 포함)"""
    if df.empty: return
    
    # 계산 전 수치형 변환 (오류 방지)
    target_cols = ['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']
    temp_df = df[target_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    t = temp_df['총매출차이'].sum()
    q = temp_df['수량차이_Impact'].sum()
    p = temp_df['단가차이_Impact'].sum()
    e = temp_df['환율차이_Impact'].sum()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 총 차이", f"{t:,.0f}")
    m2.metric("📦 수량 효과", f"{q:,.0f}")
    m3.metric("💰 단가 효과", f"{p:,.0f}")
    m4.metric("💱 환율 효과", f"{e:,.0f}")
    st.divider()

def format_analysis_table(df):
    """스타일 적용 (문자열 섞임 방지 로직 포함)"""
    # 1. 라벨 변경
    labels = get_display_labels()
    view_df = df.rename(columns=labels)

    # 2. 수치형 컬럼 강제 변환 (Unknown format code 'f' 에러 방지 핵심)
    # 한글 라벨로 바뀐 컬럼들 중 수치 데이터인 것들만 골라서 변환
    numeric_cols = list(labels.values())
    for col in numeric_cols:
        if col in view_df.columns:
            view_df[col] = pd.to_numeric(view_df[col], errors='coerce').fillna(0)

    # 3. 포맷 정의
    format_dict = {
        "계획수량": "{:,.0f}", "계획단가": "{:,.2f}", "계획금액": "{:,.0f}",
        "실적수량": "{:,.0f}", "실적단가": "{:,.2f}", "실적금액": "{:,.0f}",
        "총차이(KRW)": "{:,.0f}", "수량효과": "{:,.0f}", "단가효과": "{:,.0f}", "환율효과": "{:,.0f}"
    }

    # 4. 색상 스타일링
    def color_val(val):
        if not isinstance(val, (int, float)): return ''
        if val > 100: return 'color: #157347; font-weight: bold;' # 초록
        if val < -100: return 'color: #bb2d3b; font-weight: bold;' # 빨강
        return ''

    # 5. 스타일 적용 후 반환
    return view_df.style.format(format_dict).applymap(
        color_val, 
        subset=["총차이(KRW)", "수량효과", "단가효과", "환율효과"]
    )
