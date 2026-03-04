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
        
        # 내부 계산용 '판매금액' 생성 (수량 * 단가)
        # 이 값이 외화 기준인지 확인이 필요합니다.
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        # 1. 필터링
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 2. 계획(Plan)과 실적(Actual) 분리 및 집계
        group_cols = [COLUMNS['category_mid']]
        
        # 데이터구분('판매실적', '계획')에 따른 그룹화
        p_data = df_filtered[df_filtered[COLUMNS['division']] == '계획']
        a_data = df_filtered[df_filtered[COLUMNS['division']] == '판매실적']

        p_agg = p_data.groupby(group_cols).agg({
            COLUMNS['qty']: 'sum',
            '판매금액': 'sum',
            COLUMNS['amt_krw']: 'sum'
        }).reset_index()
        
        a_agg = a_data.groupby(group_cols).agg({
            COLUMNS['qty']: 'sum',
            '판매금액': 'sum',
            COLUMNS['amt_krw']: 'sum'
        }).reset_index()

        # 3. 데이터 병합 (Outer Join으로 한쪽만 데이터가 있는 경우 대비)
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 4. 분석용 비율 지표 계산 (0 나누기 방지)
        # 계획 단가(P_P), 계획 환율(ER_P)
        res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[COLUMNS['qty']+'_P'] if x[COLUMNS['qty']+'_P'] != 0 else 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        
        # 실제 단가(P_A), 실제 환율(ER_A)
        res['P_A'] = res.apply(lambda x: x['판매금액_A'] / x[COLUMNS['qty']+'_A'] if x[COLUMNS['qty']+'_A'] != 0 else 0, axis=1)
        res['ER_A'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        # 5. [Impact 상세 분석] - 수학적 분리
        # 수량차이 Impact: 수량의 변화량에 계획 시점의 단가와 환율을 적용
        res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P'] * res['ER_P']
        
        # 단가차이 Impact: 실제 판매된 수량에 대해 발생한 단가 변동분에 계획 환율 적용
        res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A'] - res['P_P']) * res['ER_P']
        
        # 환율차이 Impact: 실제 매출(실제 수량 * 실제 단가)에 대해 발생한 환율 변동분 적용
        res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A'] * (res['ER_A'] - res['ER_P'])
        
        # 전체 차이 합계 확인용
        res['총매출차이'] = res[COLUMNS['amt_krw']+'_A'] - res[COLUMNS['amt_krw']+'_P']

        return res
