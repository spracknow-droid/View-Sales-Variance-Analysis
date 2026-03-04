# DB 설정 및 컬럼 매핑
DB_CONFIG = {
    'db_path': 'Integrated_Sales_2526_v2601.db',
    'table_name': 'View_Integrated_Sales'
}

# 분석에 사용될 핵심 컬럼명 정의
COLUMNS = {
    'date': '매출일',
    'cust_group': '고객그룹',
    'category': '중분류',
    'division': '데이터구분',         # '판매실적' vs '계획'
    'qty': '수량',
    'amt_usd': '외화금액',
    'amt_krw': '원화금액',
    'currency': '통화'
}
