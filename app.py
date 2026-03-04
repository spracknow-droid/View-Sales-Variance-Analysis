import streamlit as st
import tempfile
import os
from logic import SalesAnalyzer
from mapping import COLUMNS
import ui_components as ui  # 분리된 UI 로직 임포트

st.set_page_config(page_title="매출 분석 시스템", layout="wide")

# --- 사이드바: 설정 ---
st.sidebar.title("📁 설정")
uploaded_file = st.sidebar.file_uploader("DB 파일 업로드", type=['db'])

hierarchy_options = {"고객그룹": COLUMNS['cust_group'], "중분류": COLUMNS['category_mid'], "거래통화": COLUMNS['currency']}
selected_labels = st.sidebar.multiselect("분석 계층 순서", options=list(hierarchy_options.keys()), default=["고객그룹", "중분류", "거래통화"])
hierarchy = [hierarchy_options[label] for label in selected_labels]

# --- 메인 로직 ---
if uploaded_file and hierarchy:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 필터 UI
        sel_month = st.sidebar.selectbox("📅 분석 연월", sorted(df_raw[COLUMNS['date']].unique(), reverse=True))
        sel_groups = st.sidebar.multiselect("👥 고객그룹", sorted(df_raw[COLUMNS['cust_group']].unique()), default=sorted(df_raw[COLUMNS['cust_group']].unique()))

        # 데이터 분석 실행
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups, hierarchy)

        if not result.empty:
            st.title(f"🔍 {sel_month} 분석 리포트")
            
            # UI 컴포넌트 활용
            view_df = result.rename(columns=ui.get_display_labels())
            styled_table = ui.format_analysis_table(view_df)
            
            st.dataframe(styled_table, use_container_width=True, height=600, hide_index=True)
            
            # 다운로드 버튼
            st.download_button("📥 CSV 다운로드", view_df.to_csv(index=False).encode('utf-8-sig'), f"Analysis_{sel_month}.csv", "text/csv")
        else:
            st.warning("데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류: {e}")
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)
else:
    st.info("DB 파일을 업로드하고 분석 계층을 선택하세요.")
