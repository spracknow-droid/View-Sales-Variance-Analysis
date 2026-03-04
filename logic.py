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

        # [핵심 수정] DB에 없는 '판매금액'을 수량 * 단가로 계산해서 생성
        # 만약 단가가 외화라면, 이것이 곧 외화 기준 '판매금액'이 됩니다.
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        # 필터링
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 계획/실적 분리
        plan = df_filtered[df_filtered[COLUMNS['division']] == '계획'].copy()
        actual = df_filtered[df_filtered[COLUMNS['division']] == '판매실적'].copy()

        # 집계 (판매금액 포함)
        group_cols = [COLUMNS['category_mid']]
        agg_dict = {
            COLUMNS['qty']: 'sum',
            '판매금액': 'sum',      # 위에서 생성한 컬럼 사용
            COLUMNS['amt_krw']: 'sum'
        }
        
        p_agg = plan.groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = actual.groupby(group_cols).agg(agg_dict).reset_index()

        # 병합
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 요인 분석 계산 (Price-Volume-FX)
        # 1. 기초 값 산출 (단가 P, 환율 ER)
        res['P_P'] = res['판매금액_P'] / res[COLUMNS['qty']+'_P']
        res['ER_P'] = res[COLUMNS['amt_krw']+'_P'] / res['판매금액_P']
        
        res['P_A'] = res['판매금액_A'] / res[COLUMNS['qty']+'_A']
        res['ER_A'] = res[COLUMNS['amt_krw']+'_A'] / res['판매금액_A']
        
        res = res.fillna(0)

        # 2. Impact 계산
        # 수량차이: (실적Q - 계획Q) * 계획P * 계획ER
        res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P'] * res['ER_P']
        
        # 단가차이: 실적Q * (실적P - 계획P) * 계획ER
        res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A'] - res['P_P']) * res['ER_P']
        
        # 환율차이: 실적Q * 실적P * (실적ER - 계획ER)
        res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A'] * (res['ER_A'] - res['ER_P'])
        
        res['총매출차이'] = res[COLUMNS['amt_krw']+'_A'] - res[COLUMNS['amt_krw']+'_P']

        return res
