import streamlit as st
import pandas as pd
from mapping import COLUMNS

def get_display_labels():
    qty_nm = COLUMNS['qty']
    amt_nm = COLUMNS['amt_krw']
    date_nm = COLUMNS['date']
    return {
        date_nm: "매출연월",
        f"{qty_nm}_P": "계획수량", "단가_P": "계획단가", f"{amt_nm}_P": "계획금액",
        f"{qty_nm}_A": "실적수량", "단가_A": "실적단가", f"{amt_nm}_A": "실적금액",
        "총매출차이": "총차이(KRW)", "수량차이_Impact": "수량효과", "단가차이_Impact": "단가효과", "환율차이_Impact": "환율효과"
    }

def display_filters(df):
    """
    화면 상단에 멀티 셀렉트 필터를 배치하여 사용자가 실시간으로 View를 제어하게 합니다.
    """
    if df.empty: return df

    # 필터 레이아웃 (3컬럼: 연월, 고객그룹, 중분류 등)
    cols = st.columns(3)
    
    # 1. 매출연월 필터
    with cols[0]:
        unique_months = sorted(df[COLUMNS['date']].unique(), reverse=True)
        sel_months = st.multiselect("📅 매출연월 필터", unique_months, default=unique_months)
    
    # 2. 고객그룹 필터
    with cols[1]:
        unique_groups = sorted(df[COLUMNS['cust_group']].unique())
        sel_groups = st.multiselect("👥 고객그룹 필터", unique_groups, default=unique_groups)

    # 3. 거래통화 필터
    with cols[2]:
        unique_curr = sorted(df[COLUMNS['currency']].unique())
        sel_curr = st.multiselect("💱 거래통화 필터", unique_curr, default=unique_curr)

    # 데이터 필터링 적용
    filtered_df = df[
        (df[COLUMNS['date']].isin(sel_months)) &
        (df[COLUMNS['cust_group']].isin(sel_groups)) &
        (df[COLUMNS['currency']].isin(sel_curr))
    ]
    
    st.divider()
    return filtered_df

def format_analysis_table(df):
    """스타일 적용 및 수치형 변환"""
    labels = get_display_labels()
    view_df = df.rename(columns=labels)

    # 수치형 강제 변환 (Unknown format code 'f' 방지)
    numeric_cols = [v for k, v in labels.items() if k != COLUMNS['date']]
    for col in numeric_cols:
        if col in view_df.columns:
            view_df[col] = pd.to_numeric(view_df[col], errors='coerce').fillna(0)

    format_dict = {
        "계획수량": "{:,.0f}", "계획단가": "{:,.2f}", "계획금액": "{:,.0f}",
        "실적수량": "{:,.0f}", "실적단가": "{:,.2f}", "실적금액": "{:,.0f}",
        "총차이(KRW)": "{:,.0f}", "수량효과": "{:,.0f}", "단가효과": "{:,.0f}", "환율효과": "{:,.0f}"
    }

    def color_val(val):
        if not isinstance(val, (int, float)): return ''
        if val > 100: return 'color: #157347; font-weight: bold;'
        if val < -100: return 'color: #bb2d3b; font-weight: bold;'
        return ''

    return view_df.style.format(format_dict).applymap(color_val, subset=["총차이(KRW)", "수량효과", "단가효과", "환율효과"])
