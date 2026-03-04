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
        df[COLUMNS['division']] = df[COLUMNS['division']].astype(str).str.strip()
        df[COLUMNS['currency']] = df[COLUMNS['currency']].astype(str).str.strip()
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        return df

    def calculate_variance(self, df, target_month, selected_groups, hierarchy):
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty: return pd.DataFrame()

        group_cols = hierarchy
        qty_col, krw_col = COLUMNS['qty'], COLUMNS['amt_krw']
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 기초 지표 산출
        res['단가_P'] = res.apply(lambda x: x['판매금액_P'] / x[f'{qty_col}_P'] if x[f'{qty_col}_P'] != 0 else 0, axis=1)
        res['환율_P'] = res.apply(lambda x: x[f'{krw_col}_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        
        res['단가_A'] = res.apply(lambda x: x['판매금액_A'] / x[f'{qty_col}_A'] if x[f'{qty_col}_A'] != 0 else 0, axis=1)
        res['환율_A'] = res.apply(lambda x: x[f'{krw_col}_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        # 보정 지표 (신규 품목/통화 대응)
        res['P_P_final'] = res.apply(lambda x: x['단가_P'] if x['단가_P'] != 0 else x['단가_A'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['환율_P'] if x['환율_P'] != 0 else x['환율_A'], axis=1)

        # Impact 계산
        res['수량차이_Impact'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        res['단가차이_Impact'] = res[f'{qty_col}_A'] * (res['단가_A'] - res['P_P_final']) * res['ER_P_final']
        res['환율차이_Impact'] = res[f'{qty_col}_A'] * res['단가_A'] * (res['환율_A'] - res['ER_P_final'])
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        # [검증용 컬럼 포함하여 반환]
        final_cols = group_cols + [
            f'{qty_col}_P', '단가_P', f'{krw_col}_P', # 계획 데이터
            f'{qty_col}_A', '단가_A', f'{krw_col}_A', # 실적 데이터
            '총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'
        ]
        return res[final_cols].sort_values(group_cols)
