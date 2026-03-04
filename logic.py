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

    def calculate_variance(self, df, selected_groups, hierarchy):
        """화면 출력용 실시간 계산"""
        df_filtered = df[df[COLUMNS['cust_group']].isin(selected_groups)].copy()
        if df_filtered.empty: return pd.DataFrame()

        date_col, qty_col, krw_col = COLUMNS['date'], COLUMNS['qty'], COLUMNS['amt_krw']
        group_cols = [date_col] + hierarchy
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        res['단가_P'] = res.apply(lambda x: x['판매금액_P'] / x[f'{qty_col}_P'] if x[f'{qty_col}_P'] != 0 else 0, axis=1)
        res['환율_P'] = res.apply(lambda x: x[f'{krw_col}_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        res['단가_A'] = res.apply(lambda x: x['판매금액_A'] / x[f'{qty_col}_A'] if x[f'{qty_col}_A'] != 0 else 0, axis=1)
        res['환율_A'] = res.apply(lambda x: x[f'{krw_col}_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        res['P_P_final'] = res.apply(lambda x: x['단가_P'] if x['단가_P'] != 0 else x['단가_A'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['환율_P'] if x['환율_P'] != 0 else x['환율_A'], axis=1)

        res['수량효과'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        res['단가효과'] = res[f'{qty_col}_A'] * (res['단가_A'] - res['P_P_final']) * res['ER_P_final']
        res['환율효과'] = res[f'{qty_col}_A'] * res['단가_A'] * (res['환율_A'] - res['ER_P_final'])
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        final_cols = group_cols + [
            f'{qty_col}_P', '단가_P', f'{krw_col}_P',
            f'{qty_col}_A', '단가_A', f'{krw_col}_A',
            '총매출차이', '수량효과', '단가효과', '환율효과'
        ]
        return res[final_cols].sort_values(group_cols, ascending=[False] + [True]*len(hierarchy))

    def create_sql_view(self, hierarchy):
        """DB 내부 VIEW 생성 (소수점 정리 및 0 데이터 제거)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        view_name = "View_Sales_Analysis"  # 이름 고정
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        date_c = COLUMNS['date']
        cols_select = ", ".join([f'IFNULL("{c}", "미분류") AS "{c}"' for c in [date_c] + hierarchy])
        cols_group = ", ".join([f'"{c}"' for c in [date_c] + hierarchy])
        
        qty, u_price, amt_krw = COLUMNS['qty'], COLUMNS['unit_price'], COLUMNS['amt_krw']
        div, plan, actual = COLUMNS['division'], COLUMNS['plan_val'], COLUMNS['actual_val']

        create_query = f"""
        CREATE VIEW {view_name} AS
        WITH Base AS (
            SELECT {cols_group},
                SUM(CASE WHEN {div}='{plan}' THEN {qty} ELSE 0 END) as Q_P,
                SUM(CASE WHEN {div}='{plan}' THEN {qty} * {u_price} ELSE 0 END) as Amt_Cur_P,
                SUM(CASE WHEN {div}='{plan}' THEN {amt_krw} ELSE 0 END) as Amt_KRW_P,
                SUM(CASE WHEN {div}='{actual}' THEN {qty} ELSE 0 END) as Q_A,
                SUM(CASE WHEN {div}='{actual}' THEN {qty} * {u_price} ELSE 0 END) as Amt_Cur_A,
                SUM(CASE WHEN {div}='{actual}' THEN {amt_krw} ELSE 0 END) as Amt_KRW_A
            FROM {COLUMNS['view_name']}
            GROUP BY {cols_group}
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
        SELECT 
            {cols_group},
            ROUND(Q_P, 0) AS 계획수량, ROUND(P_P, 4) AS 계획단가, ROUND(Amt_KRW_P, 0) AS 계획금액_KRW,
            ROUND(Q_A, 0) AS 실적수량, ROUND(P_A, 4) AS 실적단가, ROUND(Amt_KRW_A, 0) AS 실적금액_KRW,
            ROUND(Amt_KRW_A - Amt_KRW_P, 0) AS 총차이_KRW,
            ROUND((Q_A - Q_P) * P_P_final * ER_P_final, 0) AS 수량효과,
            ROUND(Q_A * (P_A - P_P_final) * ER_P_final, 0) AS 단가효과,
            ROUND(Q_A * P_A * (ER_A - ER_P_final), 0) AS 환율효과
        FROM Final
        WHERE (Q_P != 0 OR Q_A != 0);
        """
        try:
            cursor.execute(create_query)
            conn.commit()
            return view_name
        except: return None
        finally: conn.close()
