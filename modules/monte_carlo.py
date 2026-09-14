from functools import reduce

import numpy as np
import pandas as pd
from modules import model_tree


def sample_leaf(row: pd.Series, n_trials: int, rng: np.random.Generator) -> np.ndarray:
    """末端ノード1つ分、distribution列に従ってn_trials件をまとめてサンプリングする"""

    dist = row.get("distribution")

    if pd.isna(dist) or dist == "":
        # 分布未設定の項目は、常に固定値(value)として扱う
        return np.full(n_trials, float(row["value"]))

    if dist == "normal":
        mean, std = float(row["param1"]), float(row["param2"])
        return rng.normal(mean, std, n_trials)

    if dist == "triangular":
        low, mode, high = float(row["param1"]), float(row["param2"]), float(row["param3"])
        return rng.triangular(low, mode, high, n_trials)

    if dist == "uniform":
        low, high = float(row["param1"]), float(row["param2"])
        return rng.uniform(low, high, n_trials)

    # 未対応の分布名の場合も、固定値にフォールバックする
    return np.full(n_trials, float(row["value"]))


def run_simulation(df: pd.DataFrame, n_trials: int = 10000, seed: int = None) -> np.ndarray:
    """全末端ノードをランダムサンプリングし、収支(ルート)の分布をn_trials件分まとめて返す"""

    rng = np.random.default_rng(seed)
    root_id = model_tree.find_root_id(df)

    # ノードごとに1回だけ、n_trials件分の配列を計算する(1件ずつ樹形図全体を回さない)
    op_funcs = {
        "add": lambda arrs: reduce(np.add, arrs),
        "subtract": lambda arrs: reduce(np.subtract, arrs),
        "multiply": lambda arrs: reduce(np.multiply, arrs),
        "divide": lambda arrs: reduce(np.divide, arrs),
    }

    cache = {}

    def calc(node_id: str) -> np.ndarray:
        if node_id in cache:
            return cache[node_id]

        row = df[df["node_id"] == node_id].iloc[0]
        children = df[df["parent_id"] == node_id].copy()

        if len(children) == 0:
            result = sample_leaf(row, n_trials, rng)
            cache[node_id] = result
            return result

        if "order" in children.columns and children["order"].notna().any():
            children = children.sort_values("order")

        child_arrays = [calc(cid) for cid in children["node_id"]]
        result = op_funcs[row["operator"]](child_arrays)
        cache[node_id] = result
        return result

    calc(root_id)
    return cache[root_id]

def auto_fill_params(row: pd.Series) -> tuple:
    """worst_value・value・best_valueから、分布ごとの標準的なparam1〜3を算出する"""

    value = row.get("value")
    worst = row.get("worst_value")
    best = row.get("best_value")
    dist = row.get("distribution")

    if pd.isna(worst) or pd.isna(best):
        return None, None, None

    lo, hi = min(worst, best), max(worst, best)

    if dist == "normal":
        mean = value if pd.notna(value) else (lo + hi) / 2
        std = (hi - lo) / 4  # 概ね95%区間がworst〜bestに収まる目安
        return mean, std, None
    elif dist == "triangular":
        mode = value if pd.notna(value) else (lo + hi) / 2
        return lo, mode, hi
    elif dist == "uniform":
        return lo, hi, None
    else:
        return None, None, None
