import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.view_name = COLUMNS['view_name']

    def get_raw_data(self):
        # View 이름에 공백이나 특수문자가 있을 수 있으므로 따옴표 처리
        query = f'SELECT * FROM "{self.view_name}"'
        return pd.read_sql(query, self.conn)

    def calculate_variance_logic(self, month, customers):
        df = self.get_raw_data()
        
        # 1. 필터링
        mask = (df[COLUMNS['date']].astype(str).str.startswith(month)) & \
               (df[COLUMNS['cust_group']].isin(customers))
        df = df[mask]
        
        if df.empty: return pd.DataFrame()

        # 2. 피벗 (실적과 계획을 가로로 결합)
        pivot = df.pivot_table(
            index=[COLUMNS['cust_group'], COLUMNS['category_mid'], COLUMNS['currency']],
            columns=COLUMNS['division'],
            values=[COLUMNS['qty'], COLUMNS['amt_usd'], COLUMNS['amt_krw']],
            aggfunc='sum'
        ).fillna(0)

        # 컬럼 레벨 평면화
        pivot.columns = [f"{c[0]}_{c[1]}" for c in pivot.columns]
        pivot = pivot.reset_index()

        # 실적/계획 컬럼 존재 여부 체크 및 변수 할당
        try:
            # 수량/단가/환율 분석을 위한 기본 필드 계산
            # 수식: 
            # 1. 수량차이 = (실적Qty - 계획Qty) * 계획단가 * 계획환율
            # 2. 단가차이 = 실적Qty * (실적Price - 계획Price) * 계획환율
            # 3. 환율차이 = 실적Qty * 실적Price * (실적ExRate - 계획ExRate)
            
            p_qty = f"{COLUMNS['qty']}_계획"
            a_qty = f"{COLUMNS['qty']}_판매실적"
            p_usd = f"{COLUMNS['amt_usd']}_계획"
            a_usd = f"{COLUMNS['amt_usd']}_판매실적"
            p_krw = f"{COLUMNS['amt_krw']}_계획"
            a_krw = f"{COLUMNS['amt_krw']}_판매실적"

            # 0 나누기 방지를 위한 계산
            pivot['P_Price'] = pivot[p_usd] / pivot[p_qty].replace(0, 1)
            pivot['P_ExRate'] = pivot[p_krw] / pivot[p_usd].replace(0, 1)
            pivot['A_Price'] = pivot[a_usd] / pivot[a_qty].replace(0, 1)
            pivot['A_ExRate'] = pivot[a_krw] / pivot[a_usd].replace(0, 1)

            # 핵심 차이 분석 로직
            pivot['수량차이_Impact'] = (pivot[a_qty] - pivot[p_qty]) * pivot['P_Price'] * pivot['P_ExRate']
            pivot['단가차이_Impact'] = pivot[a_qty] * (pivot['A_Price'] - pivot['P_Price']) * pivot['P_ExRate']
            pivot['환율차이_Impact'] = pivot[a_qty] * pivot['A_Price'] * (pivot['A_ExRate'] - pivot['P_ExRate'])
            
            pivot['총매출차이'] = pivot[a_krw] - pivot[p_krw]
            
            return pivot[[COLUMNS['cust_group'], COLUMNS['category_mid'], '총매출차이', 
                          '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']]
        except KeyError:
            return pd.DataFrame()
