import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_raw_data(self):
        conn = sqlite3.connect(self.db_path)
        # 뷰 이름에 공백이 있을 수 있으므로 대괄호 사용
        query = f'SELECT * FROM [{COLUMNS["view_name"]}]'
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    def calculate_variance(self, df, month, customers):
        # 1. 필터링 (선택한 달과 고객그룹)
        mask = (df[COLUMNS['date']].astype(str).str.startswith(month)) & \
               (df[COLUMNS['cust_group']].isin(customers))
        f_df = df[mask].copy()
        
        if f_df.empty: return pd.DataFrame()

        # 2. 피벗팅: 데이터구분을 열로 올려서 '계획'과 '실적'을 한 줄에 배치
        pivot = f_df.pivot_table(
            index=[COLUMNS['cust_group'], COLUMNS['category_mid'], COLUMNS['currency']],
            columns=COLUMNS['division'],
            values=[COLUMNS['qty'], COLUMNS['amt_usd'], COLUMNS['amt_krw']],
            aggfunc='sum'
        ).fillna(0)

        # 컬럼명 단순화 (예: 수량_계획, 수량_판매실적)
        pivot.columns = [f"{c[0]}_{c[1]}" for c in pivot.columns]
        pivot = pivot.reset_index()

        # 3. 분석 변수 설정 (에러 방지를 위해 컬럼 존재 확인)
        try:
            p_qty, a_qty = f"{COLUMNS['qty']}_계획", f"{COLUMNS['qty']}_판매실적"
            p_usd, a_usd = f"{COLUMNS['amt_usd']}_계획", f"{COLUMNS['amt_usd']}_판매실적"
            p_krw, a_krw = f"{COLUMNS['amt_krw']}_계획", f"{COLUMNS['amt_krw']}_판매실적"

            # 단가 및 환율 역산 (0 나누기 방지)
            pivot['P_Price'] = pivot[p_usd] / pivot[p_qty].replace(0, 1)
            pivot['P_ExRate'] = pivot[p_krw] / pivot[p_usd].replace(0, 1)
            pivot['A_Price'] = pivot[a_usd] / pivot[a_qty].replace(0, 1)
            pivot['A_ExRate'] = pivot[a_krw] / pivot[a_usd].replace(0, 1)

            # [핵심 로직] Price-Volume-FX 분리
            # 1. 수량차이: (실적수량 - 계획수량) * 계획단가 * 계획환율
            pivot['수량차이_Impact'] = (pivot[a_qty] - pivot[p_qty]) * pivot['P_Price'] * pivot['P_ExRate']
            # 2. 단가차이: 실적수량 * (실적단가 - 계획단가) * 계획환율
            pivot['단가차이_Impact'] = pivot[a_qty] * (pivot['A_Price'] - pivot['P_Price']) * pivot['P_ExRate']
            # 3. 환율차이: 실적수량 * 실적단가 * (실적환율 - 계획환율)
            pivot['환율차이_Impact'] = pivot[a_qty] * pivot['A_Price'] * (pivot['A_ExRate'] - pivot['P_ExRate'])
            
            pivot['총매출차이'] = pivot[a_krw] - pivot[p_krw]
            
            return pivot
        except KeyError:
            return pd.DataFrame()
