import streamlit as st
import tempfile
import os
import pandas as pd
from logic import SalesAnalyzer
from mapping import COLUMNS

# 페이지 설정
st.set_page_config(page_title="매출 변동 요인 분석 시스템", layout="wide")

st.sidebar.title("📁 설정 및 데이터")

# 1. DB 파일 업로드
uploaded_file = st.sidebar.file_uploader("SQLite DB 파일을 업로드하세요", type=['db'])

# 2. 분석 계층 순서 설정 (사용자가 드래그/선택하여 순서 변경 가능)
hierarchy_options = {
    "고객그룹": COLUMNS['cust_group'],
    "중분류": COLUMNS['category_mid'],
    "거래통화": COLUMNS['currency']
}

st.sidebar.subheader("📊 분석 계층 순서")
selected_labels = st.sidebar.multiselect(
    "순서대로 선택하세요 (먼저 선택한 것이 상위 계층이 됩니다)",
    options=list(hierarchy_options.keys()),
    default=["고객그룹", "중분류", "거래통화"]
)

# 라벨을 실제 DB 컬럼명으로 변환
hierarchy = [hierarchy_options[label] for label in selected_labels]

if uploaded_file and len(hierarchy) > 0:
    # 임시 파일 생성하여 DB 로드
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 사이드바 필터 설정
        months = sorted(df_raw[COLUMNS['date']].unique(), reverse=True)
        sel_month = st.sidebar.selectbox("📅 분석 대상 연월", months)
        
        groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 분석 대상 고객그룹", groups, default=groups)

        # 분석 실행 (logic.py 호출)
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups, hierarchy)

        if not result.empty:
            st.title(f"🔍 {sel_month} 매출 변동 요인 분석 (검증 View)")
            st.info(f"계층 구조: {' ➡️ '.join(selected_labels)}")

            # --- 화면 표시용 컬럼명 매핑 ---
            qty_nm = COLUMNS['qty']
            amt_nm = COLUMNS['amt_krw']
            
            display_labels = {
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
            
            # 컬럼명 변경
            view_df = result.rename(columns=display_labels)

            # --- 스타일 및 포맷팅 ---
            # 1. 숫자 포맷 정의 (천단위 콤마, 소수점)
            format_dict = {
                "계획수량": "{:,.0f}", "계획단가(외화)": "{:,.2f}", "계획금액(KRW)": "{:,.0f}",
                "실적수량": "{:,.0f}", "실적단가(외화)": "{:,.2f}", "실적금액(KRW)": "{:,.0f}",
                "총차이(KRW)": "{:,.0f}", "수량효과": "{:,.0f}", "단가효과": "{:,.0f}", "환율효과": "{:,.0f}"
            }

            # 2. 색상 강조 (양수: 파랑, 음수: 빨강)
            def color_variance(val):
                if isinstance(val, (int, float)):
                    color = '#d1e7dd' if val > 0 else '#f8d7da' if val < 0 else 'white'
                    return f'background-color: {color}'
                return ''

            # 테이블 출력
            st.dataframe(
                view_df.style.format(format_dict)
                .applymap(color_variance, subset=["총차이(KRW)", "수량효과", "단가효과", "환율효과"]),
                use_container_width=True,
                height=700,
                hide_index=True
            )

            # 3. 데이터 다운로드 버튼 (CSV)
            csv = view_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 분석 결과 CSV 다운로드",
                data=csv,
                file_name=f"Sales_Analysis_{sel_month}.csv",
                mime="text/csv",
            )
            
        else:
            st.warning("선택한 조건에 해당하는 데이터가 존재하지 않습니다.")

    except Exception as e:
        st.error(f"⚠️ 실행 중 오류가 발생했습니다: {e}")
        st.exception(e) # 상세 에러 로그 표시
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

elif not uploaded_file:
    st.info("왼쪽 사이드바에서 DB 파일을 업로드하여 분석을 시작하세요.")
else:
    st.warning("최소 하나 이상의 분석 계층(고객그룹, 중분류 등)을 선택해야 합니다.")
