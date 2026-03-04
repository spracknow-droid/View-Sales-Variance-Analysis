import streamlit as st
import tempfile
import os
from logic import SalesAnalyzer
from mapping import COLUMNS
import ui_components as ui

st.set_page_config(page_title="Sales Analysis System", layout="wide")

# --- 사이드바: 파일 업로드만 남김 ---
st.sidebar.title("📁 데이터 소스")
uploaded_file = st.sidebar.file_uploader("분석할 SQLite DB 업로드", type=['db'])

# --- 분석 계층 고정 (중분류 > 고객그룹 > 거래통화) ---
# 사용자가 변경할 필요가 없으므로 내부 변수로 고정합니다.
FIXED_HIERARCHY = [
    COLUMNS['category_mid'],  # 중분류
    COLUMNS['cust_group'],    # 고객그룹
    COLUMNS['currency']       # 거래통화
]

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 1. 전체 데이터 분석 실행 (고정된 계층 구조 사용)
        all_groups = df_raw[COLUMNS['cust_group']].unique()
        result = analyzer.calculate_variance(df_raw, all_groups, FIXED_HIERARCHY)

        if not result.empty:
            st.title("🔍 매출 변동 요인 상세 분석 View")
            st.caption("분석 기준: 중분류 > 고객그룹 > 거래통화 (고정)")

            # 2. 상단 필터 컴포넌트 (실시간 필터링)
            filtered_result = ui.display_filters(result)
            
            # 3. 스타일 적용 및 테이블 출력
            styled_table = ui.format_analysis_table(filtered_result)
            st.dataframe(styled_table, use_container_width=True, height=750, hide_index=True)

            # 4. 하단 기능 버튼
            c1, c2, _ = st.columns([1.5, 2, 5])
            with c1:
                if st.button("🛠️ DB 내 분석 VIEW 생성"):
                    # SQL VIEW 생성 시에도 고정된 계층 사용
                    v_name = analyzer.create_sql_view(FIXED_HIERARCHY)
                    if v_name: st.success(f"'{v_name}' 생성 완료!")
            with c2:
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        label="📥 VIEW가 포함된 DB 다운로드",
                        data=f,
                        file_name="Sales_Analysis_Fixed.db",
                        mime="application/x-sqlite3"
                    )
        else:
            st.warning("데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")
    finally:
        # 필요 시 임시 파일 삭제 로직 추가 가능
        pass
else:
    st.info("분석을 시작하려면 왼쪽 사이드바에서 DB 파일을 업로드해 주세요.")
