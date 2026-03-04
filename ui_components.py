import streamlit as st
import pandas as pd
from mapping import COLUMNS

def get_display_labels():
    qty_nm = COLUMNS['qty']
    amt_nm = COLUMNS['amt_krw']
    date_nm = COLUMNS['date']
    return {
        date_nm: "매출연월", # 연월 컬럼 추가
        f"{qty_nm}_P": "계획수량", "단가_P": "계획단가", f"{amt_nm}_P": "계획금액",
        f"{qty_nm}_A": "실적수량", "단가_A": "실적단가", f"{amt_nm}_A": "실적금액",
        "총매출차이": "총차이(KRW)", "수량차이_Impact": "수량효과", "단가차이_Impact": "단가효과", "환율차이_Impact": "환율효과"
    }

def display_summary_metrics(df):
    if df.empty: return
    target_cols = ['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']
    temp_df = df[target_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    t, q, p, e = temp_df.sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 누적 총 차이", f"{t:,.0f}")
    m2.metric("📦 수량 효과", f"{q:,.0f}")
    m3.metric("💰 단가 효과", f"{p:,.0f}")
    m4.metric("💱 환율 효과", f"{e:,.0f}")
    st.divider()

def format_analysis_table(df):
    labels = get_display_labels()
    view_df = df.rename(columns=labels)

    # 수치형 변환 (매출연월은 제외)
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
