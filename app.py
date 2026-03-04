import streamlit as st
import tempfile
import os
import sqlite3
from logic import SalesAnalyzer
from mapping import COLUMNS
import ui_components as ui

# 페이지 설정
st.set_page_config(page_title="Sales Analysis DB Builder", layout="wide")

st.sidebar.title("📁 DB 분석 및 VIEW 생성")

# 1. 원본 DB 업로드
uploaded_file = st.sidebar.file_uploader("분석할 SQLite DB 업로드", type=['db'])

# 2. 분석 계층 설정 (이 순서가 SQL GROUP BY 순서가 됩니다)
hierarchy_options = {
    "고객그룹": COLUMNS['cust_group'],
    "중분류": COLUMNS['category_mid'],
    "거래통화": COLUMNS['currency']
}

st.sidebar.subheader("📊 분석 계층 순서")
selected_labels = st.sidebar.multiselect(
    "VIEW에 반영할 계층 순서",
    options=list(hierarchy_options.keys()),
    default=["고객그룹", "중분류", "거래통화"]
)
hierarchy = [hierarchy_options[label] for label in selected_labels]

if uploaded_file and len(hierarchy) > 0:
    # 임시 경로에 업로드된 DB 복사 (쓰기 권한 확보)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 필터 UI
        months = sorted(df_raw[COLUMNS['date']].unique(), reverse=True)
        sel_month = st.sidebar.selectbox("📅 분석 연월 선택", months)
        
        groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 대상 고객그룹", groups, default=groups)

        # --- 메인 화면 ---
        st.title(f"🔍 {sel_month} 분석 및 SQL VIEW 빌더")
        
        # 3. 분석 실행 (Python 메모리 상의 결과 확인용)
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups, hierarchy)

        if not result.empty:
            # 4. [핵심] DB 내부에 SQL VIEW 생성 버튼
            if st.button("🛠️ 분석 로직을 DB 내 VIEW로 생성"):
                view_name = analyzer.create_sql_view(sel_month, hierarchy)
                if view_name:
                    st.success(f"✅ DB 내부에 가상 테이블 '{view_name}'이(가) 성공적으로 생성되었습니다!")
                else:
                    st.error("❌ VIEW 생성에 실패했습니다.")

            # 5. 화면 표시 (데이터 검증용)
            view_df = result.rename(columns=ui.get_display_labels())
            st.dataframe(ui.format_analysis_table(view_df), use_container_width=True, hide_index=True)

            # 6. [결과물 다운로드] VIEW가 포함된 DB 파일 자체를 다운로드
            with open(tmp_path, "rb") as f:
                st.download_button(
                    label="📥 분석 VIEW가 심어진 DB 다운로드",
                    data=f,
                    file_name=f"Sales_Analysis_{sel_month.replace('-', '')}.db",
                    mime="application/x-sqlite3"
                )
        else:
            st.warning("데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")
    finally:
        # 분석 종료 후 임시 파일 삭제는 신중해야 함 (다운로드 버튼 클릭 시점 고려)
        pass 

elif not uploaded_file:
    st.info("왼쪽에서 DB를 업로드하면 분석이 시작됩니다.")
