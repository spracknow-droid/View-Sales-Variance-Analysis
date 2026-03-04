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
    # 1. 임시 파일 생성 및 업로드 데이터 복사
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()
        all_groups = df_raw[COLUMNS['cust_group']].unique()

        st.title("🔍 매출 변동 요인 분석 상세 View")

        # 2. 분석 실행 (Python 메모리 상의 결과)
        result = analyzer.calculate_variance(df_raw, all_groups, FIXED_HIERARCHY)

        if not result.empty:
            # 3. 상단 필터 및 테이블 표시 (항상 노출)
            filtered_result = ui.display_filters(result)
            styled_table = ui.format_analysis_table(filtered_result)
            st.dataframe(styled_table, use_container_width=True, height=650, hide_index=True)

            st.divider()

            # 4. [통합 버튼] VIEW 생성 후 즉시 다운로드 버튼 활성화
            # 버튼 클릭 시 DB 내부에 VIEW를 물리적으로 심습니다.
            if st.button("🚀 분석 VIEW가 포함된 DB 생성 및 다운로드 준비", use_container_width=True):
                v_name = analyzer.create_sql_view(FIXED_HIERARCHY)
                
                if v_name:
                    st.success(f"✅ DB 내부에 가상 테이블('{v_name}')이 성공적으로 심어졌습니다!")
                    
                    with open(tmp_path, "rb") as f:
                        st.download_button(
                            label="📥 생성된 DB 파일 다운로드 받기",
                            data=f,
                            file_name=f"Sales_Analysis_Report.db",
                            mime="application/x-sqlite3",
                            use_container_width=True
                        )
                else:
                    st.error("VIEW 생성 중 오류가 발생했습니다.")
        else:
            st.warning("분석할 수 있는 데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")
else:
    st.info("왼쪽 사이드바에서 DB 파일을 업로드하면 분석이 시작됩니다.")
