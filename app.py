import streamlit as st
import tempfile
import os
from logic import SalesAnalyzer
from mapping import COLUMNS
import ui_components as ui

st.set_page_config(page_title="Sales Analysis DB Builder", layout="wide")

st.sidebar.title("⚙️ 시스템 설정")
uploaded_file = st.sidebar.file_uploader("분석할 SQLite DB 업로드", type=['db'])

# 계층 구조 고정 (중분류 > 고객그룹 > 거래통화)
FIXED_HIERARCHY = [COLUMNS['category_mid'], COLUMNS['cust_group'], COLUMNS['currency']]

if uploaded_file:
    # 1. 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()
        all_groups = df_raw[COLUMNS['cust_group']].unique()

        st.title("🔍 매출 변동 요인 분석 상세 View")

        # 2. 분석 실행 (화면 표시용)
        result = analyzer.calculate_variance(df_raw, all_groups, FIXED_HIERARCHY)

        if not result.empty:
            # 3. 상단 필터 및 테이블 표시
            filtered_result = ui.display_filters(result)
            styled_table = ui.format_analysis_table(filtered_result)
            st.dataframe(styled_table, use_container_width=True, height=650, hide_index=True)

            st.divider()

            # ---------------------------------------------------------
            # 4. [진짜 통합 버튼] 딱 이거 하나만 존재합니다.
            # ---------------------------------------------------------
            # 미리 VIEW를 생성해둔 뒤 다운로드 버튼에 바로 데이터로 넘깁니다.
            analyzer.create_sql_view(FIXED_HIERARCHY) 
            
            with open(tmp_path, "rb") as f:
                st.download_button(
                    label="🚀 분석 VIEW 포함하여 DB 파일 즉시 다운로드",
                    data=f,
                    file_name="Sales_Analysis_Report.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
            # ---------------------------------------------------------

        else:
            st.warning("분석할 데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")
else:
    st.info("왼쪽에서 DB 파일을 업로드하세요.")
