import pandas as pd
import graphviz

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

def build_tree_graph(result_df: pd.DataFrame) -> graphviz.Digraph:
    """計算済みのDataFrameから、値と演算子を表示した樹形図を作成する"""

    op_symbol = {
        "add": "+",
        "subtract": "−",
        "multiply": "×",
        "divide": "÷",
    }

    dot = graphviz.Digraph()
    dot.attr(rankdir="LR")  # 左から右へのツリー構造に変更
    dot.attr(nodesep="0.4", ranksep="0.8")  # LR時は間隔を広めにすると見やすい

    for _, row in result_df.iterrows():
        lines = [str(row["label"])]

        value = row.get("calculated_value")
        if pd.notna(value):
            unit = row.get("unit")
            formatted_value = format_value(value)
            if pd.notna(unit) and unit != "":
                lines.append(f"値: {formatted_value} {unit}")
            else:
                lines.append(f"値: {formatted_value}")

        operator = row.get("operator")
        if pd.notna(operator) and operator != "":
            symbol = op_symbol.get(operator, operator)
            lines.append(f"演算: {symbol}")

        dot.node(
            str(row["node_id"]),
            label="\n".join(lines),
            shape="box",
            style="rounded,filled",
            fillcolor="#f5f5f5",
        )

    for _, row in result_df.iterrows():
        parent_id = row.get("parent_id")
        if pd.notna(parent_id) and parent_id != "":
            dot.edge(str(parent_id), str(row["node_id"]))

    return dot


def render_tree_html(dot: graphviz.Digraph, height: int = 600) -> str:
    """graphvizのDigraphを、マウスホイールでの拡大縮小・ドラッグ移動が可能なHTMLに変換する"""

    svg_content = dot.pipe(format="svg").decode("utf-8")

    return f"""
    <div id="tree-container" style="width:100%; height:{height}px; border:1px solid #ddd; overflow:hidden;">
        {svg_content}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    <script>
        (function() {{
            var svgElement = document.querySelector('#tree-container svg');
            svgElement.style.width = '100%';
            svgElement.style.height = '100%';
            svgPanZoom(svgElement, {{
                zoomEnabled: true,
                controlIconsEnabled: true,
                fit: true,
                center: true,
                minZoom: 0.2,
                maxZoom: 10
            }});
        }})();
    </script>
    """

def format_value(value: float) -> str:
    """値の大きさに応じて適切な小数桁数で文字列化する"""
    if value == int(value):
        return f"{value:,.0f}"  # 整数ならそのまま
    elif abs(value) < 10:
        return f"{value:,.2f}"  # 小さい値(比率・%など)は小数2桁
    else:
        return f"{value:,.1f}"  # それ以外は小数1桁
