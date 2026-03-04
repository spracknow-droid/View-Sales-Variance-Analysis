def calculate_variance(self, df, target_month, selected_groups):
    # 1. 필터링
    df_filtered = df[(df[COLUMNS['date']] == target_month) & 
                     (df[COLUMNS['cust_group']].isin(selected_groups))].copy()
    
    if df_filtered.empty:
        return pd.DataFrame()

    # 2. 그룹화 기준 설정 (고객그룹 -> 중분류 계층 구조)
    group_cols = [COLUMNS['cust_group'], COLUMNS['category_mid']]
    
    p_data = df_filtered[df_filtered[COLUMNS['division']] == '계획']
    a_data = df_filtered[df_filtered[COLUMNS['division']] == '판매실적']

    # 3. 집계 및 병합
    agg_dict = {COLUMNS['qty']: 'sum', '판매금액': 'sum', COLUMNS['amt_krw']: 'sum'}
    p_agg = p_data.groupby(group_cols).agg(agg_dict).reset_index()
    a_agg = a_data.groupby(group_cols).agg(agg_dict).reset_index()

    res = pd.merge(p_agg, a_agg, on=group_cols, how='outer', suffixes=('_P', '_A')).fillna(0)

    # 4. 분석 지표 계산 (P, ER) 및 Impact 계산
    # (이전 계산 로직 동일 수행...)
    res['P_P'] = res.apply(lambda x: x['판매금액_P'] / x[COLUMNS['qty']+'_P'] if x[COLUMNS['qty']+'_P'] != 0 else 0, axis=1)
    res['ER_P'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_P'] / x['판매금액_P'] if x['판매금액_P'] != 0 else 0, axis=1)
    res['P_A'] = res.apply(lambda x: x['판매금액_A'] / x[COLUMNS['qty']+'_A'] if x[COLUMNS['qty']+'_A'] != 0 else 0, axis=1)
    res['ER_A'] = res.apply(lambda x: x[COLUMNS['amt_krw']+'_A'] / x['판매금액_A'] if x['판매금액_A'] != 0 else 0, axis=1)

    res['수량차이_Impact'] = (res[COLUMNS['qty']+'_A'] - res[COLUMNS['qty']+'_P']) * res['P_P'] * res['ER_P']
    res['단가차이_Impact'] = res[COLUMNS['qty']+'_A'] * (res['P_A'] - res['P_P']) * res['ER_P']
    res['환율차이_Impact'] = res[COLUMNS['qty']+'_A'] * res['P_A'] * (res['ER_A'] - res['ER_P'])
    res['총매출차이'] = res[COLUMNS['amt_krw']+'_A'] - res[COLUMNS['amt_krw']+'_P']

    # 5. 보기 좋게 정렬
    return res.sort_values(group_cols)
