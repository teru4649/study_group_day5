import pandas as pd
from modules import model_tree


def calc_tornado_data(df: pd.DataFrame):
    """各末端ノードのworst_value/best_valueが収支(ルート)に与える影響幅を計算する"""

    root_id = model_tree.find_root_id(df)

    # 基準値(全項目を元のvalueのまま計算した場合の収支)
    base_result = model_tree.calc_all(df)
    base_value = base_result.loc[base_result["node_id"] == root_id, "calculated_value"].iloc[0]

    # 末端ノード(演算子を持たない行)だけを対象にする
    leaf_mask = df["operator"].isna() | (df["operator"] == "")
    leaf_df = df[leaf_mask]

    records = []
    for _, row in leaf_df.iterrows():
        node_id = row["node_id"]
        worst = row.get("worst_value")
        best = row.get("best_value")

        # worst_value・best_valueが未設定の項目はトルネードの対象外
        if pd.isna(worst) or pd.isna(best):
            continue

        # その項目だけをworst_valueに差し替えて再計算
        df_worst = df.copy()
        df_worst.loc[df_worst["node_id"] == node_id, "value"] = worst
        result_worst = model_tree.calc_all(df_worst)
        value_at_worst = result_worst.loc[result_worst["node_id"] == root_id, "calculated_value"].iloc[0]

        # その項目だけをbest_valueに差し替えて再計算
        df_best = df.copy()
        df_best.loc[df_best["node_id"] == node_id, "value"] = best
        result_best = model_tree.calc_all(df_best)
        value_at_best = result_best.loc[result_best["node_id"] == root_id, "calculated_value"].iloc[0]

        records.append({
            "node_id": node_id,
            "label": row["label"],
            "low": min(value_at_worst, value_at_best),
            "high": max(value_at_worst, value_at_best),
            "impact": abs(value_at_best - value_at_worst),
        })

    tornado_df = pd.DataFrame(records)
    if len(tornado_df) > 0:
        # 影響が大きい項目ほどグラフの上に来るよう並び替え
        tornado_df = tornado_df.sort_values("impact", ascending=True)

    return tornado_df, base_value
