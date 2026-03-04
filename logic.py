import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_raw_data(self):
        """DB에서 데이터를 로드하고 기초 가공을 수행합니다."""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM {COLUMNS['view_name']}"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # 데이터구분 값 공백 제거 및 문자열 처리
        df[COLUMNS['division']] = df[COLUMNS['division']].astype(str).str.strip()
        
        # 내부 계산용 '판매금액' 생성 (수량 * 단가)
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        """계산 통화 불일치를 보정한 매출 변동 요인 분석을 수행합니다."""
        
        # 1. 필터링
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 2. 계획/실적 분리 및 집계
        group_cols = [COLUMNS['cust_group'], COLUMNS['category_mid']]
        agg_cols = {COLUMNS['qty']: 'sum', '판매금액': 'sum', COLUMNS['amt_krw']: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_cols).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_cols).reset_index()

        # 3. 데이터 병합
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 4. 계획 지표 산출 (기준점)
        res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[COLUMNS['qty']+'_P'] if x[COLUMNS['qty']+'_P'] != 0 else 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x['판매금액_P'] != 0 and x['amt_krw_P'] / x['판매금액_P'] or 0, axis=1) # 단순화된 환율계산

        # 5. [핵심] 통화 불일치 보정형 실적 지표 산출
        def get_adjusted_actuals(row):
            qty_a = row[COLUMNS['qty']+'_A']
            amt_cur_a = row['판매금액_A']
            amt_krw_a = row['amt_krw_A']
            er_p = row['ER_P']
            
            if qty_a == 0:
                return pd.Series([0, 0], index=['P_A_adj', 'ER_A_adj'])
            
            # 실제 환율 (계산상 환율)
            er_a = amt_krw_a / amt_cur_a if amt_cur_a != 0 else 0
            
            # [통화 보정 로직]
            # 계획 환율이 100 이상(예: USD/KRW)인데 실적 환율이 1에 가깝다면 (실적이 KRW 거래)
            # 단가 왜곡을 막기 위해 실적 단가를 계획 환율로 정규화함
            if er_p > 100 and (er_a >= 0.9 and er_a <= 1.1):
                p_a_adj = (amt_krw_a / er_p) / qty_a
                er_a_adj = er_p # 환율 차이를 0으로 보거나 미세 조정
            else:
                p_a_adj = amt_cur_a / qty_a
                er_a_adj = er_a
                
            return pd.Series([p_a_adj, er_a_adj], index=['P_A_adj', 'ER_A_adj'])

        res[['P_A_adj', 'ER_A_adj']] = res.apply(get_adjusted_actuals, axis=1)

        # 6. 신규 품목(계획이 없는 경우) 추가 보정
        res['P_P_final'] = res.apply(lambda x: x['P_P'] if x['P_P'] != 0 else x['P_A_adj'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['ER_P'] if x['ER_P'] != 0 else x['ER_A_adj'], axis=1)

        # 7. Impact 계산 (보정된 지표 기준)
        # 수량차이
        res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P_final'] * res['ER_P_final']
        
        # 단가차이 (정규화된 단가 사용으로 폭등 방지)
        res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A_adj'] - res['P_P_final']) * res['ER_P_final']
        
        # 환율차이 (정규화된 환율 사용으로 폭락 방지)
        res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A_adj'] * (res['ER_A_adj'] - res['ER_P_final'])
        
        # 총매출차이
        res['총매출차이'] = res['amt_krw_A'] - res['amt_krw_P']

        # 8. 정렬 및 반환
        return res.sort_values([COLUMNS['cust_group'], '총매출차이'], ascending=[True, False])
