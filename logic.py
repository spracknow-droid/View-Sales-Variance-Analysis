import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        """생성자: DB 경로를 인자로 받아 저장합니다."""
        self.db_path = db_path

    def get_raw_data(self):
        """DB에서 데이터를 로드하고 공백 제거 및 수치 정규화를 수행합니다."""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM {COLUMNS['view_name']}"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # 데이터 클렌징
        df[COLUMNS['division']] = df[COLUMNS['division']].astype(str).str.strip()
        df[COLUMNS['currency']] = df[COLUMNS['currency']].astype(str).str.strip()
        
        # 내부 계산용 '판매금액' 생성
        df['판매금액'] = df[COLUMNS['qty']] * df[COLUMNS['unit_price']]
        
        return df

    def calculate_variance(self, df, selected_groups, hierarchy):
        """지정된 계층 구조에 따라 매출 변동 요인을 분석합니다."""
        
        # 1. 필터링 (고객그룹 기준)
        df_filtered = df[df[COLUMNS['cust_group']].isin(selected_groups)].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()

        # 2. 그룹핑 컬럼 설정 (연월 + 사용자 지정 계층)
        date_col = COLUMNS['date']
        group_cols = [date_col] + hierarchy
        
        qty_col, krw_col = COLUMNS['qty'], COLUMNS['amt_krw']
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        # 3. 데이터 병합
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 4. 요인별 지표 산출
        res['단가_P'] = res.apply(lambda x: x['판매금액_P'] / x[f'{qty_col}_P'] if x[f'{qty_col}_P'] != 0 else 0, axis=1)
        res['환율_P'] = res.apply(lambda x: x[f'{krw_col}_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        
        res['단가_A'] = res.apply(lambda x: x['판매금액_A'] / x[f'{qty_col}_A'] if x[f'{qty_col}_A'] != 0 else 0, axis=1)
        res['환율_A'] = res.apply(lambda x: x[f'{krw_col}_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        # 5. 신규 품목 보정
        res['P_P_final'] = res.apply(lambda x: x['단가_P'] if x['단가_P'] != 0 else x['단가_A'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['환율_P'] if x['환율_P'] != 0 else x['환율_A'], axis=1)

        # 6. Impact 계산
        res['수량차이_Impact'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        res['단가차이_Impact'] = res[f'{qty_col}_A'] * (res['단가_A'] - res['P_P_final']) * res['ER_P_final']
        res['환율차이_Impact'] = res[f'{qty_col}_A'] * res['단가_A'] * (res['환율_A'] - res['ER_P_final'])
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        # 7. 결과 구성
        final_cols = group_cols + [
            f'{qty_col}_P', '단가_P', f'{krw_col}_P',
            f'{qty_col}_A', '단가_A', f'{krw_col}_A',
            '총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'
        ]
        return res[final_cols].sort_values(group_cols, ascending=[False] + [True]*len(hierarchy))

    def create_sql_view(self, hierarchy):
        """DB 내부에 상세 분석 지표를 포함한 SQL VIEW를 생성합니다."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        view_name = "View_Sales_Analysis_Detailed"
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        all_cols = [COLUMNS['date']] + hierarchy
        cols_str = ", ".join([f'"{c}"' for c in all_cols])
        
        # 필드 매핑
        qty = COLUMNS['qty']
        u_price = COLUMNS['unit_price']
        amt_krw = COLUMNS['amt_krw']
        div = COLUMNS['division']
        plan = COLUMNS['plan_val']
        actual = COLUMNS['actual_val']

        create_query = f"""
        CREATE VIEW {view_name} AS
        WITH Base AS (
            SELECT {cols_str},
                SUM(CASE WHEN {div}='{plan}' THEN {qty} ELSE 0 END) as Q_P,
                SUM(CASE WHEN {div}='{plan}' THEN {qty} * {u_price} ELSE 0 END) as Amt_Cur_P,
                SUM(CASE WHEN {div}='{plan}' THEN {amt_krw} ELSE 0 END) as Amt_KRW_P,
                SUM(CASE WHEN {div}='{actual}' THEN {qty} ELSE 0 END) as Q_A,
                SUM(CASE WHEN {div}='{actual}' THEN {qty} * {u_price} ELSE 0 END) as Amt_Cur_A,
                SUM(CASE WHEN {div}='{actual}' THEN {amt_krw} ELSE 0 END) as Amt_KRW_A
            FROM {COLUMNS['view_name']}
            GROUP BY {cols_str}
        ),
        Metrics AS (
            SELECT *,
                CASE WHEN Q_P != 0 THEN Amt_Cur_P / Q_P ELSE 0 END as P_P,
                CASE WHEN Amt_Cur_P != 0 THEN Amt_KRW_P / Amt_Cur_P ELSE 0 END as ER_P,
                CASE WHEN Q_A != 0 THEN Amt_Cur_A / Q_A ELSE 0 END as P_A,
                CASE WHEN Amt_Cur_A != 0 THEN Amt_KRW_A / Amt_Cur_A ELSE 0 END as ER_A
            FROM Base
        ),
        Final AS (
            SELECT *,
                CASE WHEN P_P != 0 THEN P_P ELSE P_A END as P_P_final,
                CASE WHEN ER_P != 0 THEN ER_P ELSE ER_A END as ER_P_final
            FROM Metrics
        )
        SELECT {cols_str},
            Q_P as "계획수량", P_P as "계획단가", Amt_KRW_P as "계획금액_KRW",
            Q_A as "실적수량", P_A as "실적단가", Amt_KRW_A as "실적금액_KRW",
            (Amt_KRW_A - Amt_KRW_P) as "총차이_KRW",
            (Q_A - Q_P) * P_P_final * ER_P_final as "수량효과",
            Q_A * (P_A - P_P_final) * ER_P_final as "단가효과",
            Q_A * P_A * (ER_A - ER_P_final) as "환율효과"
        FROM Final;
        """
        try:
            cursor.execute(create_query)
            conn.commit()
            return view_name
        except:
            return None
        finally:
            conn.close()
