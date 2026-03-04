import streamlit as st
import tempfile
import os
import plotly.express as px
from logic import SalesAnalyzer
from mapping import COLUMNS

st.set_page_config(page_title="반도체 소재 매출 분석", layout="wide")

st.sidebar.title("📁 데이터 소스")
uploaded_file = st.sidebar.file_uploader("DB 파일 업로드", type=['db'])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 필터 제어
        months = sorted(df_raw[COLUMNS['date']].astype(str).str[:7].unique(), reverse=True)
        sel_month = st.sidebar.selectbox("📅 분석 연월", months)
        
        groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 고객그룹", groups, default=groups)

        # 계산 실행
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups)

        if not result.empty:
            st.title(f"📈 {sel_month} 매출 변동 요인 분석")
            
            # 상단 지표
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 차이(KRW)", f"{result['총매출차이'].sum():,.0f}")
            c2.metric("수량 효과", f"{result['수량차이_Impact'].sum():,.0f}")
            c3.metric("단가 효과", f"{result['단가차이_Impact'].sum():,.0f}")
            c4.metric("환율 효과", f"{result['환율차이_Impact'].sum():,.0f}")

            # Waterfall 차트 대용 바 차트
            st.divider()
            st.subheader("중분류별 차이 기여도")
            plot_df = result.melt(id_vars=[COLUMNS['category_mid']], 
                                  value_vars=['수량차이_Impact', '단가차이_Impact', '환율차이_Impact'])
            fig = px.bar(plot_df, x=COLUMNS['category_mid'], y='value', color='variable', 
                         title="요인별 Impact (Positive: 호재, Negative: 악재)")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("상세 데이터")
            st.dataframe(result, use_container_width=True)
        else:
            st.warning("분석할 수 있는 세트(계획+실적)가 해당 월에 존재하지 않습니다.")

    finally:
        os.remove(tmp_path)
else:
    st.info("사이드바에서 Integrated_Sales_...db 파일을 업로드해주세요.")
