import streamlit as st
import tempfile
import os
import pandas as pd
from logic import SalesAnalyzer
from mapping import COLUMNS

st.set_page_config(page_title="매출 분석 시스템", layout="wide")

st.sidebar.title("📁 데이터 및 설정")
uploaded_file = st.sidebar.file_uploader("DB 파일 업로드", type=['db'])

# --- 분석 계층 설정 UI ---
# 사용자가 원하는 순서대로 분석 축을 선택하고 드래그하여 순서를 결정할 수 있습니다.
hierarchy_options = {
    "고객그룹": COLUMNS['cust_group'],
    "중분류": COLUMNS['category_mid'],
    "거래통화": COLUMNS['currency']
}

st.sidebar.subheader("📊 분석 계층 순서")
selected_labels = st.sidebar.multiselect(
    "순서대로 선택하세요 (예: 고객->중분류->통화)",
    options=list(hierarchy_options.keys()),
    default=["고객그룹", "중분류", "거래통화"]
)

# 라벨을 실제 컬럼명으로 변환
hierarchy = [hierarchy_options[label] for label in selected_labels]

if uploaded_file and len(hierarchy) > 0:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 필터링 UI
        months = sorted(df_raw[COLUMNS['date']].unique(), reverse=True)
        sel_month = st.sidebar.selectbox("📅 분석 연월", months)
        
        groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 고객그룹", groups, default=groups)

        # [수정] hierarchy 인자를 추가하여 호출
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups, hierarchy)

        if not result.empty:
            st.title(f"🔍 {sel_month} 매출 변동 요인 View")
            st.caption(f"분석 계층: {' > '.join(selected_labels)}")

            # 숫자 포맷 및 스타일 적용
            def style_delta(val):
                color = 'red' if val < -100 else 'blue' if val > 100 else 'black'
                return f'color: {color}; font-weight: bold'

            styled_view = result.style.format({
                '총매출차이': '{:,.0f}',
                '수량차이_Impact': '{:,.0f}',
                '단가차이_Impact': '{:,.0f}',
                '환율차이_Impact': '{:,.0f}'
            }).applymap(style_delta, subset=['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'])

            st.dataframe(styled_view, use_container_width=True, height=600, hide_index=True)
        else:
            st.warning("선택한 조건에 해당하는 데이터가 없습니다.")

    except Exception as e:
        st.error(f"실행 중 오류 발생: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
elif not uploaded_file:
    st.info("왼쪽 사이드바에서 DB 파일을 업로드해주세요.")
else:
    st.warning("최소 하나 이상의 분석 계층을 선택해야 합니다.")
