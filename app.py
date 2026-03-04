import streamlit as st
import tempfile
import os
from logic import SalesAnalyzer
from mapping import COLUMNS

st.set_page_config(page_title="매출 분석 시스템 - 분석 View", layout="wide")

# 스타일 정의 (가독성을 위한 CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stExpander"] { border: 1px solid #d1d1d1; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.title("📁 데이터 관리")
uploaded_file = st.sidebar.file_uploader("분석 DB 업로드", type=['db'])

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

        # 분석 실행
        result = analyzer.calculate_variance(df_raw, sel_month, sel_groups)

        if not result.empty:
            st.title(f"🔍 {sel_month} 요인분석 통합 View")
            
            # 요약 지표 (가로형 배치)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("총 변동액", f"{result['총매출차이'].sum():,.0f} KRW")
            m2.metric("수량 영향", f"{result['수량차이_Impact'].sum():,.0f}")
            m3.metric("단가 영향", f"{result['단가차이_Impact'].sum():,.0f}")
            m4.metric("환율 영향", f"{result['환율차이_Impact'].sum():,.0f}")

            st.divider()

            # --- 그룹핑 View 구현 ---
            st.subheader("📋 중분류별 상세 분석 View")
            
            # 표시할 컬럼 정의
            view_cols = [
                COLUMNS['category_mid'], 
                '총매출차이', 
                '수량차이_Impact', 
                '단가차이_Impact', 
                '환율차이_Impact'
            ]
            
            # 스타일링: 음수는 빨간색, 양수는 파란색
            def color_variance(val):
                color = '#ff4b4b' if val < 0 else '#1c83e1' if val > 0 else 'black'
                return f'color: {color}'

            # 데이터프레임 스타일 적용
            styled_df = result[view_cols].style\
                .format(precision=0, thousands=",")\
                .applymap(color_variance, subset=['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'])\
                .background_gradient(cmap='Blues', subset=['총매출차이'], low=0.1, high=0.5)

            st.dataframe(styled_df, use_container_width=True, height=600)

            # 다운로드 버튼 (엑셀 보고용)
            csv = result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 현재 View 내보내기 (CSV)", csv, f"Sales_View_{sel_month}.csv", "text/csv")

        else:
            st.warning("선택한 조건에 해당하는 데이터(계획/실적 쌍)가 없습니다.")

    except Exception as e:
        st.error(f"실행 중 오류 발생: {e}")
    finally:
        os.remove(tmp_path)
