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
        # 내부 계산용 판매금액 생성
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 그룹핑 기준: 고객그룹 + 중분류
        group_cols = [COLUMNS['cust_group'], COLUMNS['category_mid']]
        
        p_data = df_filtered[df_filtered[COLUMNS['division']] == '계획']
        a_data = df_filtered[df_filtered[COLUMNS['division']] == '판매실적']

        agg_dict = {COLUMNS['qty']: 'sum', '판매금액': 'sum', COLUMNS['amt_krw']: 'sum'}
        p_agg = p_data.groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = a_data.groupby(group_cols).agg(agg_dict).reset_index()

        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 변동 요인 계산 (0 나누기 방지)
        res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[COLUMNS['qty']+'_P'] if x[COLUMNS['qty']+'_P'] != 0 else 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        res['P_A'] = res.apply(lambda x: x['판매금액_A'] / x[COLUMNS['qty']+'_A'] if x[COLUMNS['qty']+'_A'] != 0 else 0, axis=1)
        res['ER_A'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P'] * res['ER_P']
        res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A'] - res['P_P']) * res['ER_P']
        res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A'] * (res['ER_A'] - res['ER_P'])
        res['총매출차이'] = res[COLUMNS['amt_krw']+'_A'] - res[COLUMNS['amt_krw']+'_P']

        return res.sort_values([COLUMNS['cust_group'], '총매출차이'], ascending=[True, False])
