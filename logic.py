import sqlite3
from mapping import COLUMNS

class SalesAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_raw_data(self):
        """DB에서 기초 데이터를 로드합니다."""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM {COLUMNS['view_name']}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    def create_sql_view(self, target_month, hierarchy_cols):
        """
        [핵심] DB 내부에 물리적 복사본이 아닌 '가상 VIEW'를 생성합니다.
        원본 데이터가 변경되어도 이 VIEW를 조회하면 최신 분석 결과가 나옵니다.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. 기존 동일 이름의 VIEW 삭제
        view_name = f"Analysis_View_{target_month.replace('-', '')}"
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        # 2. 계층 구조에 따른 그룹핑 컬럼 생성
        cols_str = ", ".join(hierarchy_cols)
        
        # 3. SQL VIEW 생성 쿼리 (가상 테이블 정의)
        # 계획(Plan)과 실적(Actual)을 Join하여 요인분석 수식을 SQL로 직접 박아넣습니다.
        create_view_query = f"""
        CREATE VIEW {view_name} AS
        WITH Base AS (
            SELECT 
                {cols_str},
                SUM(CASE WHEN {COLUMNS['division']} = '{COLUMNS['plan_val']}' THEN {COLUMNS['qty']} ELSE 0 END) as Q_P,
                SUM(CASE WHEN {COLUMNS['division']} = '{COLUMNS['plan_val']}' THEN {COLUMNS['qty']} * {COLUMNS['unit_price']} ELSE 0 END) as Amt_Cur_P,
                SUM(CASE WHEN {COLUMNS['division']} = '{COLUMNS['plan_val']}' THEN {COLUMNS['amt_krw']} ELSE 0 END) as Amt_KRW_P,
                SUM(CASE WHEN {COLUMNS['division']} = '{COLUMNS['actual_val']}' THEN {COLUMNS['qty']} ELSE 0 END) as Q_A,
                SUM(CASE WHEN {COLUMNS['division']} = '{COLUMNS['actual_val']}' THEN {COLUMNS['qty']} * {COLUMNS['unit_price']} ELSE 0 END) as Amt_Cur_A,
                SUM(CASE WHEN {COLUMNS['division']} = '{COLUMNS['actual_val']}' THEN {COLUMNS['amt_krw']} ELSE 0 END) as Amt_KRW_A
            FROM {COLUMNS['view_name']}
            WHERE {COLUMNS['date']} = '{target_month}'
            GROUP BY {cols_str}
        ),
        Metrics AS (
            SELECT *,
                CASE WHEN Q_P != 0 THEN Amt_Cur_P / Q_P ELSE 0 END as P_P,
                CASE WHEN Amt_Cur_P != 0 THEN Amt_KRW_P / Amt_Cur_P ELSE 0 END as ER_P,
                CASE WHEN Q_A != 0 THEN Amt_Cur_A / Q_A ELSE 0 END as P_A,
                CASE WHEN Amt_Cur_A != 0 THEN Amt_KRW_A / Amt_Cur_A ELSE 0 END as ER_A
            FROM Base
        )
        SELECT *,
            (Q_A - Q_P) * P_P * ER_P as Q_Impact,
            Q_A * (P_A - P_P) * ER_P as P_Impact,
            Q_A * P_A * (ER_A - ER_P) as ER_Impact,
            Amt_KRW_A - Amt_KRW_P as Total_Diff
        FROM Metrics;
        """
        
        try:
            cursor.execute(create_view_query)
            conn.commit()
            return view_name
        except Exception as e:
            print(f"VIEW 생성 오류: {e}")
            return None
        finally:
            conn.close()
