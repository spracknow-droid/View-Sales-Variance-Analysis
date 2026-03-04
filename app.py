import streamlit as st
import tempfile
import os
from logic import SalesAnalyzer
from mapping import COLUMNS
import ui_components as ui

st.set_page_config(page_title="Dynamic Sales Analysis View", layout="wide")

st.sidebar.title("⚙️ 시스템 설정")
uploaded_file = st.sidebar.file_uploader("DB 파일 업로드", type=['db'])

# 그룹핑 기준 설정 (연월은 기본 포함)
h_options = {"고객그룹": COLUMNS['cust_group'], "중분류": COLUMNS['category_mid'], "거래통화": COLUMNS['currency']}
selected_labels = st.sidebar.multiselect("분석 계층 순서 설정", options=list(h_options.keys()), default=list(h_options.keys()))
hierarchy = [h_options[label] for label in selected_labels]

if uploaded_file and hierarchy:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 1. 전체 데이터 분석 (Logic 실행)
        # 사이드바의 sel_groups 대신 전체 그룹을 먼저 넘깁니다.
        all_groups = df_raw[COLUMNS['cust_group']].unique()
        result = analyzer.calculate_variance(df_raw, all_groups, hierarchy)

        if not result.empty:
            st.title("🔍 매출 변동 요인 상세 분석 View")
            
            # 2. [신규] 상단 필터 컴포넌트 호출
            # 사용자가 선택한 필터에 따라 result 데이터가 즉시 필터링됩니다.
            filtered_result = ui.display_filters(result)
            
            # 3. 스타일 적용 및 테이블 출력
            styled_table = ui.format_analysis_table(filtered_result)
            st.dataframe(styled_table, use_container_width=True, height=700, hide_index=True)

            # 4. 부가 기능 (VIEW 생성 및 다운로드)
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🛠️ DB 내 분석 VIEW 생성"):
                    v_name = analyzer.create_sql_view(hierarchy)
                    if v_name: st.success(f"'{v_name}' 생성!")
            with c2:
                with open(tmp_path, "rb") as f:
                    st.download_button("📥 VIEW가 포함된 DB 다운로드", f, "Sales_Analysis.db")
        else:
            st.warning("데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류: {e}")
    finally:
        if os.path.exists(tmp_path): pass
else:
    st.info("왼쪽에서 DB 업로드 후 계층 순서를 지정하세요.")
