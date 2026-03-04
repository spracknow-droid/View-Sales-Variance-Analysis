import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_raw_data(self):
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM {COLUMNS['view_name']}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        # 1. 필터링 (해당 월 & 선택된 고객그룹)
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 2. 계획(Plan)과 실적(Actual) 분리
        plan = df_filtered[df_filtered[COLUMNS['division']] == '계획'].copy()
        actual = df_filtered[df_filtered[COLUMNS['division']] == '판매실적'].copy()

        # 3. 집계 (중분류별로 합산)
        group_cols = [COLUMNS['category_mid']]
        p_agg = plan.groupby(group_cols).agg({
            COLUMNS['qty']: 'sum',
            COLUMNS['amt_cur']: 'sum',
            COLUMNS['amt_krw']: 'sum'
        }).reset_index()
        
        a_agg = actual.groupby(group_cols).agg({
            COLUMNS['qty']: 'sum',
            COLUMNS['amt_cur']: 'sum',
            COLUMNS['amt_krw']: 'sum'
        }).reset_index()

        # 4. 데이터 병합 (Outer Join)
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 5. 요인 분석 계산 (중요 로직)
        # 단가(P) = 판매금액 / 수량, 환율(ER) = 장부금액 / 판매금액
        
        # 계획 수치 계산
        res['P_P'] = res[COLUMNS['amt_cur']+'_P'] / res[COLUMNS['qty']+'_P']
        res['ER_P'] = res[COLUMNS['amt_krw']+'_P'] / res[COLUMNS['amt_cur']+'_P']
        
        # 실제 수치 계산
        res['P_A'] = res[COLUMNS['amt_cur']+'_A'] / res[COLUMNS['qty']+'_A']
        res['ER_A'] = res[COLUMNS['amt_krw']+'_A'] / res[COLUMNS['amt_cur']+'_A']
        
        res = res.fillna(0) # 0으로 나누기 방지

        # [Impact 계산 공식]
        # 1. 수량차이: (실적Qty - 계획Qty) * 계획단가 * 계획환율
        res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P'] * res['ER_P']
        
        # 2. 단가차이: 실적Qty * (실적단가 - 계획단가) * 계획환율
        res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A'] - res['P_P']) * res['ER_P']
        
        # 3. 환율차이: 실적Qty * 실적단가 * (실적환율 - 계획환율)
        res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A'] * (res['ER_A'] - res['ER_P'])
        
        # 4. 총 매출 차이
        res['총매출차이'] = res[COLUMNS['amt_krw']+'_A'] - res[COLUMNS['amt_krw']+'_P']

        return res
