import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from logic import calculate_variance
from mapping import DB_CONFIG

st.set_page_config(page_title="매출 차이 분석 대시보드", layout="wide")

st.title("📊 매출 차이 분석 (Price-Volume-FX)")
st.markdown("고객그룹 및 중분류별 계획 대비 실적 분석")

# DB 연결
def get_data():
    conn = sqlite3.connect(DB_CONFIG['db_path'])
    # mapping.py에 정의된 기본 뷰를 가져옴
    query = "SELECT * FROM View_Integrated_Sales"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

try:
    df_raw = get_data()
    
    # 사이드바 필터
    st.sidebar.header("조회 조건")
    months = sorted(df_raw['매출일'].str[:7].unique(), reverse=True)
    selected_month = st.sidebar.selectbox("매출연월 선택", months)
    
    cust_groups = df_raw['고객그룹'].unique()
    selected_cust = st.sidebar.multiselect("고객그룹 선택", cust_groups, default=cust_groups)

    # 로직 파일을 통한 데이터 가공
    df_analyzed = calculate_variance(df_raw, selected_month, selected_cust)

    # 메인 지표 (KPI)
    total_var = df_analyzed['총매출차이'].sum()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 매출 차이 (KRW)", f"{total_var:,.0f}")
    col2.metric("수량 영향", f"{df_analyzed['수량차이_Impact'].sum():,.0f}")
    col3.metric("단가 영향", f"{df_analyzed['단가차이_Impact'].sum():,.0f}")
    col4.metric("환율 영향", f"{df_analyzed['환율차이_Impact'].sum():,.0f}")

    # 차트: 중분류별 차이 분석
    st.subheader(f"{selected_month} 요인별 매출 변동 기여도")
    fig_df = df_analyzed.melt(id_vars=['중분류'], value_vars=['수량차이_Impact', '단가차이_Impact', '환율차이_Impact'], var_name='요인', value_name='금액')
    fig = px.bar(fig_df, x='중분류', y='금액', color='요인', barmode='group', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    # 상세 데이터 테이블
    st.subheader("상세 분석 데이터")
    st.dataframe(df_analyzed.style.format("{:,.0f}", subset=['계획원화매출', '실적원화매출', '총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']))

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
