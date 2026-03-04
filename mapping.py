# 실제 DB View의 컬럼명과 100% 매칭
COLUMNS = {
    'view_name': 'View_Integrated_Sales',
    'date': '매출연월',        # YYYY-MM
    'cust_group': '고객그룹', # 필터링 축 1
    'category_mid': '중분류', # 필터링 축 2
    'division': '데이터구분', # '판매실적' vs '계획' 구분자
    'qty': '수량',
    'amt_cur': '판매금액',  # (수량×판매단가) 
    'amt_krw': '장부금액',
    'currency': '거래통화'
}
