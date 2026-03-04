import streamlit as st
import sqlite3
import tempfile
import os
import pandas as pd
from mapping import COLUMNS, get_table_names
from logic import SalesAnalyzer

st.set_page_config(page_title="Sales Variance Dashboard", layout="wide")

st.sidebar.title("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("Integrated_Sales DB 파일을 선택하세요", type=['db', 'sqlite', 'sqlite3'])

if uploaded_file is not None:
    # 1. 업로드된 파일을 임시 파일로 저장 (sqlite3 연결을 위해)
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_db_path = tmp_file.name

    try:
        # 2. 분석 엔진 초기화 및 데이터 로드
        analyzer = SalesAnalyzer(tmp_db_path)
        df_raw = analyzer.get_raw_data()
        
        # 3. 사이드바 필터 구성
        st.sidebar.divider()
        months = sorted(df_raw[COLUMNS['date']].astype(str).str[:7].unique(), reverse=True)
        selected_month = st.sidebar.selectbox("매출연월", months)
        
        cust_groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        selected_cust = st.sidebar.multiselect("고객그룹", cust_groups, default=cust_groups)

        # 4. 분석 실행
        df_analyzed = analyzer.calculate_variance_logic(selected_month, selected_cust)

        # 5. 결과 출력
        st.title(f"📊 {selected_month} 매출 차이 분석")
        
        if not df_analyzed.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("총 차이(KRW)", f"{df_analyzed['총매출차이'].sum():,.0f}")
            m2.metric("수량 영향", f"{df_analyzed['수량차이_Impact'].sum():,.0f}")
            m3.metric("단가 영향", f"{df_analyzed['단가차이_Impact'].sum():,.0f}")
            m4.metric("환율 영향", f"{df_analyzed['환율차이_Impact'].sum():,.0f}")
            
            st.divider()
            st.subheader("중분류별 분석 상세")
            st.dataframe(df_analyzed, use_container_width=True)
        else:
            st.warning("선택한 조건에 해당하는 데이터(실적/계획 세트)가 없습니다.")

    finally:
        # 사용 후 임시 파일 삭제
        os.remove(tmp_db_path)
else:
    st.info("왼쪽 사이드바에서 DB 파일을 업로드해 주세요.")
