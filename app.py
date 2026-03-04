import streamlit as st
import tempfile
import os
import pandas as pd
# 파일이 같은 경로에 있는지 확인하세요
try:
    from logic import SalesAnalyzer
    from mapping import COLUMNS
except ImportError:
    st.error("❌ logic.py 또는 mapping.py 파일을 찾을 수 없습니다. 파일 위치를 확인해주세요.")
    st.stop()

st.set_page_config(page_title="매출 분석 시스템", layout="wide")

st.sidebar.title("📁 데이터 소스")
uploaded_file = st.sidebar.file_uploader("DB 파일 업로드", type=['db'])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        analyzer = SalesAnalyzer(tmp_path)
        df_raw = analyzer.get_raw_data()

        # 필터링
        months = sorted(df_raw[COLUMNS['date']].unique(), reverse=True)
        sel_month = st.sidebar.selectbox("📅 분석 연월", months)
        
        groups = sorted(df_raw[COLUMNS['cust_group']].unique())
        sel_groups = st.sidebar.multiselect("👥 고객그룹", groups, default=groups)

        # 계산 실행
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups)

        if not result.empty:
            st.title(f"🔍 {sel_month} 매출 변동 요인 View")
            
            # View 전용 데이터 가공 (그룹핑 강조)
            view_df = result[[
                COLUMNS['cust_group'], 
                COLUMNS['category_mid'], 
                '총매출차이', 
                '수량차이_Impact', 
                '단가차이_Impact', 
                '환율차이_Impact'
            ]].copy()

            # 스타일링: 음수 빨강, 양수 파랑
            def style_delta(val):
                color = 'red' if val < -100 else 'blue' if val > 100 else 'black'
                return f'color: {color}; font-weight: bold'

            st.subheader("📊 항목별 상세 분석 (그룹핑 View)")
            
            # Pandas Styler를 이용한 표 구성
            styled_view = view_df.style.format({
                '총매출차이': '{:,.0f}',
                '수량차이_Impact': '{:,.0f}',
                '단가차이_Impact': '{:,.0f}',
                '환율차이_Impact': '{:,.0f}'
            }).applymap(style_delta, subset=['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'])

            # 인덱스를 숨기고 화면에 꽉 차게 표시
            st.dataframe(styled_view, use_container_width=True, height=600, hide_index=True)
            
            # 하단 요약 (그룹별 합계 View 추가 가능)
            st.divider()
            summary = view_df.groupby(COLUMNS['cust_group'])['총매출차이'].sum().reset_index()
            st.write("📌 고객그룹별 총 차이 요약")
            st.table(summary.style.format({'총매출차이': '{:,.0f}'}))

        else:
            st.warning("분석 가능한 데이터(계획/실적 쌍)가 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
else:
    st.info("왼쪽 사이드바에서 DB 파일을 업로드하면 분석 View가 생성됩니다.")
