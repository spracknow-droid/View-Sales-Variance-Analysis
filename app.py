import streamlit as st
import tempfile
import os
from logic import SalesAnalyzer
from mapping import COLUMNS
import ui_components as ui

st.set_page_config(page_title="Global Sales Analysis Builder", layout="wide")

st.sidebar.title("📁 분석 설정")
uploaded_file = st.sidebar.file_uploader("DB 파일 업로드", type=['db'])

hierarchy_options = {"고객그룹": COLUMNS['cust_group'], "중분류": COLUMNS['category_mid'], "거래통화": COLUMNS['currency']}
selected_labels = st.sidebar.multiselect("분석 계층 (연월은 자동 포함)", options=list(hierarchy_options.keys()), default=["고객그룹", "중분류", "거래통화"])
hierarchy = [hierarchy_options[label] for label in selected_labels]

if uploaded_file and hierarchy:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 고객그룹 필터만 유지 (연월 선택 제거)
        all_groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 대상 고객그룹", all_groups, default=all_groups)

        # 분석 실행
        result = analyzer.calculate_variance(df_raw, sel_groups, hierarchy)

        if not result.empty:
            st.title("🔍 전사 매출 변동 요인 분석 리포트")
            
            # 요약 지표 및 표 출력
            ui.display_summary_metrics(result)
            styled_table = ui.format_analysis_table(result)
            st.dataframe(styled_table, use_container_width=True, height=700, hide_index=True)

            # DB 내 SQL VIEW 생성 및 다운로드
            if st.button("🛠️ DB 내에 분석 VIEW 생성"):
                v_name = analyzer.create_sql_view(hierarchy)
                if v_name: st.success(f"'{v_name}' 생성 완료!")
            
            with open(tmp_path, "rb") as f:
                st.download_button("📥 VIEW가 포함된 DB 다운로드", f, "Sales_Analysis_Full.db", "application/x-sqlite3")
        else:
            st.warning("데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류: {e}")
    finally:
        if os.path.exists(tmp_path): pass
else:
    st.info("DB 업로드 및 분석 계층을 선택하세요.")
