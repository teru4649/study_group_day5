import pandas as pd


def find_root_id(df: pd.DataFrame) -> str:
    """parent_idが空(NaN)の行をルートノードとして特定する"""
    root_rows = df[df["parent_id"].isna() | (df["parent_id"] == "")]
    if len(root_rows) == 0:
        raise ValueError("ルートノード(parent_idが空の行)が見つかりません")
    if len(root_rows) > 1:
        raise ValueError("ルートノードが複数あります(parent_idが空の行が2つ以上)")
    return root_rows.iloc[0]["node_id"]


def calc_value(node_id: str, df: pd.DataFrame, cache: dict) -> float:
    """指定ノードの値を再帰的に計算する(子ノードがあれば演算、なければvalueをそのまま返す)"""

    # 既に計算済みならキャッシュを返す(同じノードを何度も計算しない)
    if node_id in cache:
        return cache[node_id]

    node = df[df["node_id"] == node_id]
    if len(node) == 0:
        raise ValueError(f"node_id '{node_id}' がCSV内に見つかりません")
    node = node.iloc[0]

    children = df[df["parent_id"] == node_id].copy()

    # 子ノードがない = 末端ノード → valueをそのまま採用
    if len(children) == 0:
        if pd.isna(node["value"]):
            raise ValueError(f"末端ノード '{node_id}' にvalueが設定されていません")
        result = float(node["value"])
        cache[node_id] = result
        return result

    # 子ノードがある = 中間ノード → operatorに従って演算
    if "order" in children.columns and children["order"].notna().any():
        children = children.sort_values("order")

    child_values = [calc_value(cid, df, cache) for cid in children["node_id"]]

    operator = node["operator"]
    if pd.isna(operator) or operator == "":
        raise ValueError(f"中間ノード '{node_id}' にoperatorが設定されていません")

    if operator == "add":
        result = sum(child_values)
    elif operator == "subtract":
        result = child_values[0] - sum(child_values[1:])
    elif operator == "multiply":
        result = 1
        for v in child_values:
            result *= v
    elif operator == "divide":
        result = child_values[0]
        for v in child_values[1:]:
            result /= v
    else:
        raise ValueError(f"未対応のoperatorです: '{operator}' (node_id: {node_id})")

    cache[node_id] = result
    return result


def calc_all(df: pd.DataFrame) -> pd.DataFrame:
    """全ノードの計算結果を付けたDataFrameを返す"""
    cache = {}
    root_id = find_root_id(df)
    calc_value(root_id, df, cache)  # ルートから辿って全ノードを計算

    result_df = df.copy()
    result_df["calculated_value"] = result_df["node_id"].map(cache)
    return result_df
