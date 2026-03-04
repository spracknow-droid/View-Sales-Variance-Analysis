import pandas as pd
from mapping import COLUMNS

def calculate_variance(df, month, customers):
    # 1. 필터링
    df = df[(df[COLUMNS['date']].str.startswith(month)) & 
            (df[COLUMNS['cust_group']].isin(customers))]
    
    # 2. 피벗팅 (한 행에 실적과 계획을 나란히 배치)
    pivot = df.pivot_table(
        index=[COLUMNS['cust_group'], COLUMNS['category'], COLUMNS['currency']],
        columns=COLUMNS['division'],
        values=[COLUMNS['qty'], COLUMNS['amt_usd'], COLUMNS['amt_krw']],
        aggfunc='sum'
    ).fillna(0)
    
    # 컬럼 레벨 정리
    pivot.columns = [f"{col[0]}_{col[1]}" for col in pivot.columns]
    pivot = pivot.reset_index()

    # 필요한 컬럼 매핑 (실적/계획 구분)
    # 실제 DB 값에 따라 '판매실적', '계획' 문자열 확인 필요
    p = {
        'a_qty': f"{COLUMNS['qty']}_판매실적",
        'p_qty': f"{COLUMNS['qty']}_계획",
        'a_usd': f"{COLUMNS['amt_usd']}_판매실적",
        'p_usd': f"{COLUMNS['amt_usd']}_계획",
        'a_krw': f"{COLUMNS['amt_krw']}_판매실적",
        'p_krw': f"{COLUMNS['amt_krw']}_계획"
    }

    # 3. 단가 및 환율 산출
    pivot['계획단가_USD'] = pivot[p['p_usd']] / pivot[p['p_qty']].replace(0, 1)
    pivot['계획환율'] = pivot[p['p_krw']] / pivot[p['p_usd']].replace(0, 1)
    
    pivot['실적단가_USD'] = pivot[p['a_usd']] / pivot[p['a_qty']].replace(0, 1)
    pivot['실적환율'] = pivot[p['a_krw']] / pivot[p['a_usd']].replace(0, 1)

    # 4. 차이 분석 로직 (Price-Volume-FX Variance)
    # 수량 차이: (실적수량 - 계획수량) * 계획단가 * 계획환율
    pivot['수량차이_Impact'] = (pivot[p['a_qty']] - pivot[p['p_qty']]) * pivot['계획단가_USD'] * pivot['계획환율']
    
    # 단가 차이: 실적수량 * (실적단가 - 계획단가) * 계획환율
    pivot['단가차이_Impact'] = pivot[p['a_qty']] * (pivot['실적단가_USD'] - pivot['계획단가_USD']) * pivot['계획환율']
    
    # 환율 차이: 실적수량 * 실적단가 * (실적환율 - 계획환율)
    pivot['환율차이_Impact'] = pivot[p['a_qty']] * pivot['실적단가_USD'] * (pivot['실적환율'] - pivot['계획환율'])
    
    pivot['총매출차이'] = pivot[p['a_krw']] - pivot[p['p_krw']]
    pivot['계획원화매출'] = pivot[p['p_krw']]
    pivot['실적원화매출'] = pivot[p['a_krw']]

    return pivot[[COLUMNS['category'], '계획원화매출', '실적원화매출', '총매출차이', 
                  '수량차이_Impact', '단가차이_Impact', '환율차이_Impact']]
