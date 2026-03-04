# DB 내부 실제 컬럼명 매핑
COLUMNS = {
    'view_name': 'View_Integrated_Sales',
    'date': '매출일',
    'cust_group': '고객그룹',
    'category_mid': '중분류',
    'division': '데이터구분', # '판매실적' or '계획'
    'qty': '수량',
    'amt_usd': '외화금액',
    'amt_krw': '원화금액',
    'currency': '통화'
}

def get_table_names(conn):
    """DB 내 테이블/뷰 목록 확인용"""
    import pandas as pd
    return pd.read_sql("SELECT name FROM sqlite_master WHERE type IN ('table','view')", conn)['name'].tolist()
