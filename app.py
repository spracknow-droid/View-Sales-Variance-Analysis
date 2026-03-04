if not result.empty:
    st.title(f"🔍 {sel_month} 매출 변동 상세 View")

    # 표시할 데이터 정리
    view_df = result[[
        COLUMNS['cust_group'], 
        COLUMNS['category_mid'], 
        '총매출차이', 
        '수량차이_Impact', 
        '단가차이_Impact', 
        '환율차이_Impact'
    ]]

    # 스타일링 함수: 0보다 작으면 빨간색, 크면 파란색 (텍스트만)
    def color_delta(val):
        if val < -100: color = 'red'  # 오차범위 감안
        elif val > 100: color = 'blue'
        else: color = 'black'
        return f'color: {color}'

    # 엑셀과 같은 그리드 형태의 View 생성
    st.subheader("📊 계층별 매출 변동 내역")
    
    styled_view = view_df.style.format({
        '총매출차이': '{:,.0f}',
        '수량차이_Impact': '{:,.0f}',
        '단가차이_Impact': '{:,.0f}',
        '환율차이_Impact': '{:,.0f}'
    }).applymap(color_delta, subset=['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'])

    # Streamlit 데이터프레임으로 출력 (index를 숨겨 View처럼 보이게 함)
    st.dataframe(styled_view, use_container_width=True, height=700, hide_index=True)

    # 하단에 총계 표시 (View의 완성도)
    st.info(f"💡 전체 {len(view_df)}개 항목에 대한 분석이 완료되었습니다.")
