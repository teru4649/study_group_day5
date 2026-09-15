from functools import reduce

import numpy as np
import pandas as pd
from modules import model_tree


def sample_leaf(row: pd.Series, n_trials: int, rng: np.random.Generator) -> np.ndarray:
    """末端ノード1つ分、distribution列に従ってn_trials件をまとめてサンプリングする"""

    # working_dfの該当行から、distribution列の値(文字列)を取得する
    dist = row.get("distribution")

    # ---① distributionが空欄(NaN)または空文字列の場合---
    # → 「不確実性を持たせない」項目として、常に固定値(基準値)を返す
    if pd.isna(dist) or dist == "":
        return np.full(n_trials, float(row["value"]))

    # ---② distributionが"normal"(正規分布)の場合---
    # ⚠️ 注意:ここは文字列の完全一致(==)で判定している。
    #    "normal"以外の表記(例:"Normal"、"normal "など前後の空白や大文字小文字違い)は
    #    この条件にヒットせず、下の「未対応」分岐に落ちてしまう
    if dist == "normal":
        mean, std = float(row["param1"]), float(row["param2"])
        return rng.normal(mean, std, n_trials)

    # ---③ distributionが"triangular"(三角分布)の場合---
    # ⚠️ ②と同じ注意点(完全一致判定)がここにも当てはまる
    if dist == "triangular":
        low, mode, high = float(row["param1"]), float(row["param2"]), float(row["param3"])
        return rng.triangular(low, mode, high, n_trials)

    # ---④ distributionが"uniform"(一様分布)の場合---
    # ⚠️ ②と同じ注意点(完全一致判定)がここにも当てはまる
    if dist == "uniform":
        low, high = float(row["param1"]), float(row["param2"])
        return rng.uniform(low, high, n_trials)

    # ---⑤ ここに到達するのは、①〜④のどれにも一致しなかった場合---
    # ⚠️⚠️ 最重要ポイント:
    #    「未対応の分布名」として説明されているが、実際には
    #    「distributionに何らかの文字列は入っているが、正確に
    #     normal/triangular/uniformのどれとも完全一致しなかった」
    #    場合も、この行に落ちてくる。
    #    この場合、param1〜3にどんな値を入れても一切使われず、
    #    常にvalue(基準値)固定として扱われてしまう。
    #    → これは「値を変えても結果が変わらない」という
    #      ご報告の症状と、完全に一致する挙動です。
    return np.full(n_trials, float(row["value"]))


def run_simulation(df: pd.DataFrame, n_trials: int = 10000, seed: int = None) -> np.ndarray:
    """全末端ノードをランダムサンプリングし、収支(ルート)の分布をn_trials件分まとめて返す"""

    # 乱数生成器を1つ作成(この関数が呼ばれるたびに新しい乱数列になる)
    rng = np.random.default_rng(seed)

    # ツリーのルートノード(収支)のnode_idを特定
    root_id = model_tree.find_root_id(df)

    # 四則演算の記号(operator列の文字列)と、実際の計算処理(NumPy配列同士の演算)の対応表
    # ⚠️ ここも②③④と同様、operator列の文字列が"add"/"subtract"/"multiply"/"divide"の
    #    どれとも完全一致しない場合、後述のcalc関数内でKeyErrorになる想定だが、
    #    今回の症状(エラーではなく無反応)とは一致しないため、こちらは今回の主原因ではなさそう
    op_funcs = {
        "add": lambda arrs: reduce(np.add, arrs),
        "subtract": lambda arrs: reduce(np.subtract, arrs),
        "multiply": lambda arrs: reduce(np.multiply, arrs),
        "divide": lambda arrs: reduce(np.divide, arrs),
    }

    # 計算済みノードを覚えておくキャッシュ(この関数の呼び出し1回につき、新しく作られる)
    cache = {}

    def calc(node_id: str) -> np.ndarray:
        """指定ノードのn_trials件分の値(NumPy配列)を、再帰的に計算する"""

        # 既に計算済みなら、キャッシュから返す(同じノードを2度計算しない)
        if node_id in cache:
            return cache[node_id]

        # このノード自身の情報(行)を取得
        row = df[df["node_id"] == node_id].iloc[0]
        # このノードの子ノード(parent_idが自分と一致する行)を取得
        children = df[df["parent_id"] == node_id].copy()

        # ---子ノードが無い = 末端ノード---
        # → sample_leaf関数(上で定義したもの)でランダムサンプリングする
        if len(children) == 0:
            result = sample_leaf(row, n_trials, rng)
            cache[node_id] = result
            return result

        # ---子ノードがある = 中間ノード---
        # 演算の順序が意味を持つ場合(引き算・割り算)、order列で並び替える
        if "order" in children.columns and children["order"].notna().any():
            children = children.sort_values("order")

        # 各子ノードの値(配列)を、再帰的に計算して集める
        child_arrays = [calc(cid) for cid in children["node_id"]]

        # operator列に従って、子ノード同士を演算する
        result = op_funcs[row["operator"]](child_arrays)
        cache[node_id] = result
        return result

    # ルートノードから計算を開始(再帰的に全ノードが辿られる)
    calc(root_id)

    # ルートノード(収支)の計算結果(n_trials件分の配列)だけを返す
    return cache[root_id]


def auto_fill_params(row: pd.Series, default_dist: str = "triangular") -> tuple:
    """worst_value・value・best_valueから、分布ごとの標準的なparam1〜3を算出する。
    distributionが未設定の場合は、default_dist(既定:triangular)を採用する"""

    value = row.get("value")
    worst = row.get("worst_value")
    best = row.get("best_value")
    dist = row.get("distribution")

    # worst_value・best_valueのどちらかが空欄なら、自動計算をあきらめて(None×4)を返す
    if pd.isna(worst) or pd.isna(best):
        return None, None, None, None

    # distributionが空欄なら、既定の"triangular"を採用
    if pd.isna(dist) or dist == "":
        dist = default_dist

    lo, hi = min(worst, best), max(worst, best)

    # ⚠️ ここでも同様に、dist(distribution)の文字列と"normal"等の完全一致判定を行っている
    if dist == "normal":
        mean = value if pd.notna(value) else (lo + hi) / 2
        std = (hi - lo) / 4
        return dist, mean, std, None
    elif dist == "triangular":
        mode = value if pd.notna(value) else (lo + hi) / 2
        return dist, lo, mode, hi
    elif dist == "uniform":
        return dist, lo, hi, None
    else:
        # ⚠️ ここに落ちると、自動入力自体が「対象外」として何もしないまま終わる
        return None, None, None, None
