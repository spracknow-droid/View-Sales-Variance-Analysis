# 실제 DB View의 컬럼명과 100% 매칭
COLUMNS = {
    'view_name': 'View_Integrated_Sales',
    'date': '매출연월',        # YYYY-MM
    'cust_group': '고객그룹',  # 필터링 축 1
    'category_mid': '중분류',  # 필터링 축 2
    'division': '데이터구분',  # '판매실적' vs '판매계획' 구분자
    'qty': '수량',
    'unit_price': '판매단가',  # DB에 존재하는 단가 컬럼
    'amt_krw': '장부금액',    # 원화 기준 최종 매출
    'currency': '거래통화',
    
    # 데이터 구분을 위한 실제 DB 값 정의
    'plan_val': '판매계획',
    'actual_val': '판매실적'
}
