import streamlit as st
from mapping import COLUMNS

def get_display_labels():
    """화면 표시용 컬럼명 매핑 반환"""
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

def format_analysis_table(df):
    """데이터프레임에 스타일과 포맷 적용"""
    format_dict = {
        "계획수량": "{:,.0f}", "계획단가(외화)": "{:,.2f}", "계획금액(KRW)": "{:,.0f}",
        "실적수량": "{:,.0f}", "실적단가(외화)": "{:,.2f}", "실적금액(KRW)": "{:,.0f}",
        "총차이(KRW)": "{:,.0f}", "수량효과": "{:,.0f}", "단가효과": "{:,.0f}", "환율효과": "{:,.0f}"
    }

    def color_variance(val):
        if isinstance(val, (int, float)):
            if val > 100: return 'background-color: #d1e7dd; color: #0f5132' # 초록
            if val < -100: return 'background-color: #f8d7da; color: #842029' # 빨강
        return ''

    styled_df = df.style.format(format_dict).applymap(
        color_variance, 
        subset=["총차이(KRW)", "수량효과", "단가효과", "환율효과"]
    )
    return styled_df
