import streamlit as st
import tempfile
import os
import pandas as pd  # 초기화를 위해 필요
from logic import SalesAnalyzer
from mapping import COLUMNS

st.set_page_config(page_title="매출 분석 시스템 - 분석 View", layout="wide")

st.sidebar.title("📁 데이터 관리")
uploaded_file = st.sidebar.file_uploader("분석 DB 업로드", type=['db'])

# 1. 변수 초기화 (NameError 방지)
result = pd.DataFrame()

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 사이드바 필터
        months = sorted(df_raw[COLUMNS['date']].unique(), reverse=True)
        sel_month = st.sidebar.selectbox("📅 대상 월 선택", months)
        
        groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 고객그룹 필터", groups, default=groups)

        # 2. 계산 실행 (이 블록 안에서 result가 생성됨)
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups)

        # 3. 화면 표시 로직 (반드시 계산 실행과 같은 레벨 혹은 그 아래에 위치)
        if not result.empty:
            st.title(f"🔍 {sel_month} 매출 변동 상세 View")

            view_df = result[[
                COLUMNS['cust_group'], 
                COLUMNS['category_mid'], 
                '총매출차이', 
                '수량차이_Impact', 
                '단가차이_Impact', 
                '환율차이_Impact'
            ]]

            # 스타일링 함수 (Matplotlib 없이 작동)
            def color_delta(val):
                if val < -100: return 'color: red'
                elif val > 100: return 'color: blue'
                return 'color: black'

            st.subheader("📊 계층별 매출 변동 내역")
            
            styled_view = view_df.style.format({
                '총매출차이': '{:,.0f}',
                '수량차이_Impact': '{:,.0f}',
                '단가차이_Impact': '{:,.0f}',
                '환율차이_Impact': '{:,.0f}'
            }).applymap(color_delta, subset=['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'])

            st.dataframe(styled_view, use_container_width=True, height=700, hide_index=True)
        else:
            st.warning("분석할 수 있는 데이터가 부족합니다.")

    except Exception as e:
        st.error(f"실행 중 오류 발생: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
else:
    st.info("사이드바에서 DB 파일을 업로드해주세요.")
