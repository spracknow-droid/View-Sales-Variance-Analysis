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
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty: return pd.DataFrame()

        group_cols = [COLUMNS['cust_group'], COLUMNS['category_mid']]
        qty_col, krw_col = COLUMNS['qty'], COLUMNS['amt_krw']
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 1. 계획 지표 (기준)
        res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[f'{qty_col}_P'] if x[f'{qty_col}_P'] != 0 else 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x[f'{krw_col}_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)

        # 2. 실적 지표 및 통화 보정 로직 강화
        def get_adjusted_actuals(row):
            qty_a = row[f'{qty_col}_A']
            amt_cur_a = row['판매금액_A']   # 실적이 KRW면 이 값이 매우 큼
            amt_krw_a = row[f'{krw_col}_A']
            er_p = row['ER_P'] if row['ER_P'] != 0 else 1300 # 계획 환율 없으면 기본값(혹은 적절한 값)
            
            if qty_a == 0: return pd.Series([0, 0], index=['P_A_adj', 'ER_A_adj'])
            
            # 실제 계산상 환율 (ER_A)
            er_a = amt_krw_a / amt_cur_a if amt_cur_a != 0 else 0
            
            # [수정된 보정 조건]
            # 실적 환율이 2 미만(KRW 거래)이거나, 계획 환율보다 현저히 작을 경우 보정 실행
            if er_a < 2: 
                # KRW 매출액을 계획 환율로 나눠서 USD 단가로 강제 변환
                p_a_adj = (amt_krw_a / er_p) / qty_a
                er_a_adj = er_p # 환율 차이 노이즈 제거를 위해 계획 환율과 일치시킴
            else:
                p_a_adj = amt_cur_a / qty_a
                er_a_adj = er_a
                
            return pd.Series([p_a_adj, er_a_adj], index=['P_A_adj', 'ER_A_adj'])

        res[['P_A_adj', 'ER_A_adj']] = res.apply(get_adjusted_actuals, axis=1)

        # 3. 신규 품목 보정
        res['P_P_final'] = res.apply(lambda x: x['P_P'] if x['P_P'] != 0 else x['P_A_adj'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['ER_P'] if x['ER_P'] != 0 else x['ER_A_adj'], axis=1)

        # 4. Impact 계산
        res['수량차이_Impact'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        res['단가차이_Impact'] = res[f'{qty_col}_A'] * (res['P_A_adj'] - res['P_P_final']) * res['ER_P_final']
        res['환율차이_Impact'] = res[f'{qty_col}_A'] * res['P_A_adj'] * (res['ER_A_adj'] - res['ER_P_final'])
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        return res.sort_values([COLUMNS['cust_group'], '총매출차이'], ascending=[True, False])
