COLUMNS = {
    'view_name': 'View_Integrated_Sales',
    'date': '매출연월',
    'cust_group': '고객그룹',
    'category_mid': '중분류',
    'division': '데이터구분',
    'qty': '수량',
    'unit_price': '판매단가',  # [추가] DB에 있는 실제 단가 컬럼명
    'amt_krw': '장부금액',
    'currency': '거래통화',
    # '판매금액'은 DB에 없으므로 매핑에서 제외하거나 내부 계산용으로만 인지
}
