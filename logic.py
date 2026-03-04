import pandas as pd
import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    # ... (기존 get_raw_data, calculate_variance 로직은 유지) ...

    def create_sql_view(self, hierarchy):
        """
        [고도화] 단순 합계가 아닌, 화면의 모든 Impact 지표를 포함한 가상 VIEW를 생성합니다.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        view_name = "View_Sales_Analysis_Detailed"
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        # 계층 구조 컬럼 설정
        all_cols = [COLUMNS['date']] + hierarchy
        cols_str = ", ".join([f'"{c}"' for c in all_cols])
        
        # SQL 내부에서 계산할 필드 정의 (원본 컬럼명 매핑)
        qty = COLUMNS['qty']
        u_price = COLUMNS['unit_price']
        amt_krw = COLUMNS['amt_krw']
        div = COLUMNS['division']
        plan = COLUMNS['plan_val']
        actual = COLUMNS['actual_val']

        # 쿼리 설명: 
        # 1. Base: 계획/실적별 수량, 외화금액, 원화금액 집계
        # 2. Metrics: 단가(P), 환율(ER) 산출 및 신규 품목 보정(P_P_final)
        # 3. Final: 요인별 Impact(수량/단가/환율) 최종 계산
        create_query = f"""
        CREATE VIEW {view_name} AS
        WITH Base AS (
            SELECT 
                {cols_str},
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
        SELECT 
            {cols_str},
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
        except Exception as e:
            print(f"VIEW 생성 실패: {e}")
            return None
        finally:
            conn.close()
