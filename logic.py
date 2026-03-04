import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_raw_data(self):
        """DB에서 데이터를 로드하고 공백 제거 등 기초 가공을 수행합니다."""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM {COLUMNS['view_name']}"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # 데이터구분 및 거래통화 값의 앞뒤 공백 제거 (매칭 오류 방지)
        df[COLUMNS['division']] = df[COLUMNS['division']].astype(str).str.strip()
        df[COLUMNS['currency']] = df[COLUMNS['currency']].astype(str).str.strip()
        
        # 내부 계산용 '판매금액' 생성 (수량 * 단가)
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        
        return df

    def calculate_variance(self, df, target_month, selected_groups, hierarchy):
        """
        사용자가 지정한 계층(hierarchy) 순서에 따라 매출 변동 요인을 분석합니다.
        hierarchy: ['고객그룹', '중분류', '거래통화'] 등 사용자가 선택한 컬럼 리스트
        """
        
        # 1. 대상 월 및 고객그룹 필터링
        df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                         (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 2. 그룹핑 기준 설정 (사용자 지정 순서 반영)
        group_cols = hierarchy
        qty_col = COLUMNS['qty']
        krw_col = COLUMNS['amt_krw']
        
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        # 3. 계획(Plan)과 실적(Actual) 분리 및 집계
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        # 4. 데이터 병합 (동일 계층 내 1:1 매칭)
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 5. 요인 분석 지표 계산
        # 계획(P) 지표
        res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[f'{qty_col}_P'] if x[f'{qty_col}_P'] != 0 else 0, axis=1)
        res['ER_P'] = res.apply(lambda x: x[f'{krw_col}_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        
        # 실제(A) 지표
        res['P_A'] = res.apply(lambda x: x['판매금액_A'] / x[f'{qty_col}_A'] if x[f'{qty_col}_A'] != 0 else 0, axis=1)
        res['ER_A'] = res.apply(lambda x: x[f'{krw_col}_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        # 6. 신규 통화/품목 발생 시 보정 (계획에 없는 경우 실적값을 기준점으로 사용)
        res['P_P_final'] = res.apply(lambda x: x['P_P'] if x['P_P'] != 0 else x['P_A'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['ER_P'] if x['ER_P'] != 0 else x['ER_A'], axis=1)

        # 7. Impact 상세 분석 공식
        # 수량차이: (실적Q - 계획Q) * 계획P * 계획ER
        res['수량차이_Impact'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        
        # 단가차이: 실적Q * (실적P - 계획P) * 계획ER
        res['단가차이_Impact'] = res[f'{qty_col}_A'] * (res['P_A'] - res['P_P_final']) * res['ER_P_final']
        
        # 환율차이: 실적Q * 실적P * (실적ER - 계획ER)
        res['환율차이_Impact'] = res[f'{qty_col}_A'] * res['P_A'] * (res['ER_A'] - res['ER_P_final'])
        
        # 총 매출 차이
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        # 8. 최종 결과 가공 (사용자 지정 계층 순으로 정렬)
        final_cols = group_cols + ['총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']
        return res[final_cols].sort_values(group_cols)
