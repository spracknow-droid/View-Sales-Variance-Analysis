import streamlit as st
import pandas as pd # <-- 스타일 속성 정의 시 필요할 수 있음
from mapping import COLUMNS

def get_display_labels():
    qty_nm = COLUMNS['qty']
    amt_nm = COLUMNS['amt_krw']
    return {
        f"{qty_nm}_P": "계획수량", "단가_P": "계획단가", f"{amt_nm}_P": "계획금액",
        f"{qty_nm}_A": "실적수량", "단가_A": "실적단가", f"{amt_nm}_A": "실적금액",
        "총매출차이": "총차이(KRW)", "수량차이_Impact": "수량효과", "단가차이_Impact": "단가효과", "환율차이_Impact": "환율효과"
    }

def display_summary_metrics(df):
    if df.empty: return
    t, q, p, e = df['총매출차이'].sum(), df['수량차이_Impact'].sum(), df['단가차이_Impact'].sum(), df['환율차이_Impact'].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 총 차이", f"{t:,.0f}")
    m2.metric("📦 수량", f"{q:,.0f}")
    m3.metric("💰 단가", f"{p:,.0f}")
    m4.metric("💱 환율", f"{e:,.0f}")
    st.divider()

def format_analysis_table(df):
    view_df = df.rename(columns=get_display_labels())
    format_dict = {k: "{:,.0f}" for k in view_df.columns if "단가" not in k}
    format_dict["계획단가"] = "{:,.2f}"
    format_dict["실적단가"] = "{:,.2f}"

    def color_val(val):
        if not isinstance(val, (int, float)): return ''
        return 'color: #0f5132; font-weight: bold;' if val > 0 else 'color: #842029; font-weight: bold;' if val < 0 else ''

    return view_df.style.format(format_dict).applymap(color_val, subset=["총차이(KRW)", "수량효과", "단가효과", "환율효과"])
