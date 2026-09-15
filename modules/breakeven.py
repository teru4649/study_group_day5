import numpy as np
import pandas as pd
from modules import model_tree


def calc_breakeven_table(df: pd.DataFrame) -> tuple:
    """全末端項目について、収支を0にする損益分岐点(value)を計算し、一覧表を作る"""

    root_id = model_tree.find_root_id(df)
    base_result = model_tree.calc_all(df)
    base_root_value = base_result.loc[base_result["node_id"] == root_id, "calculated_value"].iloc[0]

    leaf_mask = df["operator"].isna() | (df["operator"] == "")
    leaf_df = df.loc[leaf_mask]

    records = []
    for _, row in leaf_df.iterrows():
        current_value = row["value"]
        node_id = row["node_id"]

        if pd.isna(current_value):
            records.append({
                "label": row["label"], "unit": row.get("unit", ""),
                "現在値": np.nan, "損益分岐点": np.nan,
                "差分": np.nan, "安全余裕率(%)": np.nan, "備考": "現在値が未設定",
            })
            continue

        solution, success = model_tree.goal_seek(df, node_id, target_root_value=0.0)

        if not success:
            records.append({
                "label": row["label"], "unit": row.get("unit", ""),
                "現在値": current_value, "損益分岐点": np.nan,
                "差分": np.nan, "安全余裕率(%)": np.nan, "備考": "分岐点が見つかりません",
            })
            continue

        diff = solution - current_value
        margin_pct = (diff / current_value * 100) if current_value != 0 else np.nan

        records.append({
            "label": row["label"], "unit": row.get("unit", ""),
            "現在値": current_value, "損益分岐点": solution,
            "差分": diff, "安全余裕率(%)": margin_pct, "備考": "",
        })

    breakeven_df = pd.DataFrame(records)
    return breakeven_df, base_root_value
