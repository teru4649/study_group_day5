import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules import sensitivity

st.title("感度分析(2項目マトリクス)")

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

# トルネードチャート等で編集済みの値があれば、それを基準にする
working_df = st.session_state.get("working_df", st.session_state["df"])

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
leaf_options = working_df.loc[leaf_mask, ["node_id", "label", "value", "worst_value", "best_value"]]

if len(leaf_options) < 2:
    st.warning("感度分析には末端項目が2つ以上必要です")
    st.stop()

label_to_id = dict(zip(leaf_options["label"], leaf_options["node_id"]))

col1, col2 = st.columns(2)
with col1:
    selected_label_x = st.selectbox("横軸の項目", options=leaf_options["label"], key="sens_x")
with col2:
    remaining_labels = [l for l in leaf_options["label"] if l != selected_label_x]
    selected_label_y = st.selectbox("縦軸の項目", options=remaining_labels, key="sens_y")

node_id_x = label_to_id[selected_label_x]
node_id_y = label_to_id[selected_label_y]

row_x = leaf_options[leaf_options["node_id"] == node_id_x].iloc[0]
row_y = leaf_options[leaf_options["node_id"] == node_id_y].iloc[0]


def default_range(row):
    """worst_value/best_valueがあればそれを、無ければvalueの±50%を初期範囲にする"""
    lo = row["worst_value"] if pd.notna(row["worst_value"]) else row["value"] * 0.5
    hi = row["best_value"] if pd.notna(row["best_value"]) else row["value"] * 1.5
    return float(min(lo, hi)), float(max(lo, hi))


default_lo_x, default_hi_x = default_range(row_x)
default_lo_y, default_hi_y = default_range(row_y)

st.subheader("動かす範囲の設定")

col3, col4 = st.columns(2)
with col3:
    range_x = st.slider(
        f"{selected_label_x} の範囲",
        min_value=float(default_lo_x - abs(default_lo_x) * 0.5 - 1),
        max_value=float(default_hi_x + abs(default_hi_x) * 0.5 + 1),
        value=(default_lo_x, default_hi_x),
    )
with col4:
    range_y = st.slider(
        f"{selected_label_y} の範囲",
        min_value=float(default_lo_y - abs(default_lo_y) * 0.5 - 1),
        max_value=float(default_hi_y + abs(default_hi_y) * 0.5 + 1),
        value=(default_lo_y, default_hi_y),
    )

steps = st.slider("分割数(格子の細かさ)", min_value=3, max_value=11, value=5, step=2)

matrix_df = sensitivity.calc_two_way_sensitivity(
    working_df, node_id_x, range_x, node_id_y, range_y, steps=steps
)

fig = go.Figure(data=go.Heatmap(
    z=matrix_df.values,
    x=matrix_df.columns,
    y=matrix_df.index,
    colorscale="RdBu",
    zmid=0,  # 収支0を色の中心にする(赤字=赤系、黒字=青系)
    colorbar=dict(title="収支"),
    text=matrix_df.values,
    texttemplate="%{text:,.0f}",
))

fig.update_layout(
    title=f"「{selected_label_x}」×「{selected_label_y}」が収支に与える影響",
    xaxis_title=selected_label_x,
    yaxis_title=selected_label_y,
    height=500,
)

st.plotly_chart(fig, use_container_width=True)

st.caption("各セルの数値は、その2項目の組み合わせにおける収支(ルートノード)の計算結果です。色が赤いほど赤字、青いほど黒字を表します。")
