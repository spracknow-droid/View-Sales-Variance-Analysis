import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_raw_data(self):
        """DB에서 데이터를 로드하고 기초 계산 컬럼을 생성합니다."""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM {COLUMNS['view_name']}"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # 데이터구분 값의 앞뒤 공백 제거 (매칭 오류 방지)
        df[COLUMNS['division']] = df[COLUMNS['division']].astype(str).str.strip()
        
        # 내부 계산용 '판매금액' 생성 (수량 * 단가)
        # DB View에 판매금액이 없으므로 수량과 단가를 곱해 외화 기준 매출을 만듭니다.
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        
        return df

    def calculate_variance(self, df, target_month, selected_groups):
        """계획 대비 실적의 차이를 분석하여 요인별 Impact를 계산합니다."""
        
        # 1. 대상 월 및 고객그룹 필터링
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 2. 계획(Plan)과 실적(Actual) 데이터 분리
        p_data = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']]
        a_data = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']]

        # 3. 그룹핑 집계 (고객그룹 + 중분류 계층 구조)
        group_cols = [COLUMNS['cust_group'], COLUMNS['category_mid']]
        agg_dict = {
            COLUMNS['qty']: 'sum',
            '판매금액': 'sum',
            COLUMNS['amt_krw']: 'sum'
        }
        
        p_agg = p_data.groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = a_data.groupby(group_cols).agg(agg_dict).reset_index()

        # 4. 데이터 병합 (Outer Join)
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 5. 요인 분석용 기초 지표 계산 (0 나누기 방지)
        # 계획/실적 단가(P) 및 환율(ER) 산출
        res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[COLUMNS['qty']+'_P'] if x[COLUMNS['qty']+'_P'] != 0 else 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        
        res['P_A'] = res.apply(lambda x: x['판매금액_A'] / x[COLUMNS['qty']+'_A'] if x[COLUMNS['qty']+'_A'] != 0 else 0, axis=1)
        res['ER_A'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        # 6. [중요] 신규 품목(계획이 0인 경우) 보정 로직
        # 계획 단가/환율이 0이면 실적 값을 빌려와서 '수량 효과'로 인식하게 함
        res['P_P_adj'] = res.apply(lambda x: x['P_P'] if x['P_P'] != 0 else x['P_A'], axis=1)
        res['ER_P_adj'] = res.apply(lambda x: x['ER_P'] if x['ER_P'] != 0 else x['ER_A'], axis=1)

        # 7. Impact 상세 분석 공식 (보정된 지표 사용)
        
        # [수량차이]: (실적Q - 계획Q) * 계획P * 계획ER
        # 신규 품목은 (실적Q - 0) * 실적P * 실적ER 이 되어 '신규 매출액 전체'가 수량 효과가 됨
        res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P_adj'] * res['ER_P_adj']
        
        # [단가차이]: 실적Q * (실적P - 계획P) * 계획ER
        # 신규 품목은 실적P - 실적P = 0 이 되어 단가 효과가 발생하지 않음
        res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A'] - res['P_P_adj']) * res['ER_P_adj']
        
        # [환율차이]: 실적Q * 실적P * (실적ER - 계획ER)
        # 신규 품목은 실적ER - 실적ER = 0 이 되어 환율 효과가 발생하지 않음
        res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A'] * (res['ER_A'] - res['ER_P_adj'])
        
        # 총 매출 차이 합계
        res['총매출차이'] = res[COLUMNS['amt_krw']+'_A'] - res[COLUMNS['amt_krw']+'_P']

        # 8. 정리 및 반환 (고객그룹별 정렬)
        final_cols = group_cols + ['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']
        return res[final_cols].sort_values([COLUMNS['cust_group'], '총매출차이'], ascending=[True, False])
