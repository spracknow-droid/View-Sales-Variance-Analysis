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
        
        # 데이터구분 값 공백 제거
        df[COLUMNS['division']] = df[COLUMNS['division']].astype(str).str.strip()
        
        # 내부 계산용 '판매금액' 생성
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
        # 집계 대상 컬럼 정의
        qty_col = COLUMNS['qty']
        krw_col = COLUMNS['amt_krw']
        
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        # 3. 데이터 병합 (suffixes 적용으로 _P, _A 생성)
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 4. 계획 지표 산출 (접미사 붙은 컬럼명 사용)
        res['P_P'] = res.apply(lambda x: x[f'{qty_col}_P'] != 0 and x['판매금액_P'] / x[f'{qty_col}_P'] or 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x['판매금액_P'] != 0 and x[f'{krw_col}_P'] / x['판매금액_P'] or 0, axis=1)

        # 5. 통화 불일치 보정형 실적 지표 산출
        def get_adjusted_actuals(row):
            qty_a = row[f'{qty_col}_A']
            amt_cur_a = row['판매금액_A']
            amt_krw_a = row[f'{krw_col}_A']
            er_p = row['ER_P']
            
            if qty_a == 0:
                return pd.Series([0, 0], index=['P_A_adj', 'ER_A_adj'])
            
            # 실제 환율
            er_a = amt_krw_a / amt_cur_a if amt_cur_a != 0 else 0
            
            # 통화 보정 로직 (USD 계획을 KRW로 실적 잡은 경우)
            if er_p > 100 and (0.9 <= er_a <= 1.1):
                p_a_adj = (amt_krw_a / er_p) / qty_a
                er_a_adj = er_p
            else:
                p_a_adj = amt_cur_a / qty_a
                er_a_adj = er_a
                
            return pd.Series([p_a_adj, er_a_adj], index=['P_A_adj', 'ER_A_adj'])

        res[['P_A_adj', 'ER_A_adj']] = res.apply(get_adjusted_actuals, axis=1)

        # 6. 신규 품목 보정 (계획 0일 때 실적값 대입)
        res['P_P_final'] = res.apply(lambda x: x['P_P'] if x['P_P'] != 0 else x['P_A_adj'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['ER_P'] if x['ER_P'] != 0 else x['ER_A_adj'], axis=1)

        # 7. Impact 계산
        # 수량차이: (실적Q - 계획Q) * 계획P * 계획ER
        res['수량차이_Impact'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        
        # 단가차이: 실적Q * (보정실적P - 계획P) * 계획ER
        res['단가차이_Impact'] = res[f'{qty_col}_A'] * (res['P_A_adj'] - res['P_P_final']) * res['ER_P_final']
        
        # 환율차이: 실적Q * 보정실적P * (보정실적ER - 계획ER)
        res['환율차이_Impact'] = res[f'{qty_col}_A'] * res['P_A_adj'] * (res['ER_A_adj'] - res['ER_P_final'])
        
        # 총매출차이
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        # 8. 정렬 및 결과 반환
        return res.sort_values([COLUMNS['cust_group'], '총매출차이'], ascending=[True, False])
