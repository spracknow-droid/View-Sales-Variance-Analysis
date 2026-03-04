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
        # 1. 필터링 (연월 필터 제거, 고객그룹만 유지)
        df_filtered = df[df[COLUMNS['cust_group']].isin(selected_groups)].copy()
        
        if df_filtered.empty: return pd.DataFrame()

        # 2. 그룹핑 컬럼에 '매출연월' 강제 포함
        date_col = COLUMNS['date']
        group_cols = [date_col] + hierarchy # 연월이 가장 앞에 오도록 설정
        
        qty_col, krw_col = COLUMNS['qty'], COLUMNS['amt_krw']
        agg_dict = {qty_col: 'sum', '판매금액': 'sum', krw_col: 'sum'}
        
        p_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['plan_val']].groupby(group_cols).agg(agg_dict).reset_index()
        a_agg = df_filtered[df_filtered[COLUMNS['division']] == COLUMNS['actual_val']].groupby(group_cols).agg(agg_dict).reset_index()

        # 3. 데이터 병합
        res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

        # 4. 요인 계산
        res['단가_P'] = res.apply(lambda x: x['판매금액_P'] / x[f'{qty_col}_P'] if x[f'{qty_col}_P'] != 0 else 0, axis=1)
        res['환율_P'] = res.apply(lambda x: x[f'{krw_col}_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
        res['단가_A'] = res.apply(lambda x: x['판매금액_A'] / x[f'{qty_col}_A'] if x[f'{qty_col}_A'] != 0 else 0, axis=1)
        res['환율_A'] = res.apply(lambda x: x[f'{krw_col}_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

        res['P_P_final'] = res.apply(lambda x: x['단가_P'] if x['단가_P'] != 0 else x['단가_A'], axis=1)
        res['ER_P_final'] = res.apply(lambda x: x['환율_P'] if x['환율_P'] != 0 else x['환율_A'], axis=1)

        res['수량차이_Impact'] = (res[f'{qty_col}_A'] - res[f'{qty_col}_P']) * res['P_P_final'] * res['ER_P_final']
        res['단가차이_Impact'] = res[f'{qty_col}_A'] * (res['단가_A'] - res['P_P_final']) * res['ER_P_final']
        res['환율차이_Impact'] = res[f'{qty_col}_A'] * res['단가_A'] * (res['환율_A'] - res['ER_P_final'])
        res['총매출차이'] = res[f'{krw_col}_A'] - res[f'{krw_col}_P']

        final_cols = group_cols + [
            f'{qty_col}_P', '단가_P', f'{krw_col}_P',
            f'{qty_col}_A', '단가_A', f'{krw_col}_A',
            '총매출차이', '수량차이_Impact', '단가차이_Impact', '환율차이_Impact'
        ]
        # 연월 순으로 정렬
        return res[final_cols].sort_values(group_cols, ascending=[False] + [True]*len(hierarchy))

    def create_sql_view(self, hierarchy):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        view_name = "View_Sales_Analysis_All_Months"
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        # SQL 그룹핑에도 연월 추가
        all_cols = [COLUMNS['date']] + hierarchy
        cols_str = ", ".join([f'"{c}"' for c in all_cols])
        
        create_query = f"""
        CREATE VIEW {view_name} AS
        SELECT {cols_str}, 
               SUM(CASE WHEN {COLUMNS['division']}='{COLUMNS['plan_val']}' THEN {COLUMNS['qty']} ELSE 0 END) as Q_Plan,
               SUM(CASE WHEN {COLUMNS['division']}='{COLUMNS['actual_val']}' THEN {COLUMNS['qty']} ELSE 0 END) as Q_Actual,
               SUM(CASE WHEN {COLUMNS['division']}='{COLUMNS['actual_val']}' THEN {COLUMNS['amt_krw']} ELSE 0 END) - 
               SUM(CASE WHEN {COLUMNS['division']}='{COLUMNS['plan_val']}' THEN {COLUMNS['amt_krw']} ELSE 0 END) as Total_Diff
        FROM {COLUMNS['view_name']}
        GROUP BY {cols_str}
        """
        try:
            cursor.execute(create_query)
            conn.commit()
            return view_name
        except:
            return None
        finally:
            conn.close()
