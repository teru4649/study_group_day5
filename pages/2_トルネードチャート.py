import streamlit as st
import plotly.graph_objects as go
from modules import tornado, model_tree

st.title("トルネードチャート")

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

if "working_df" not in st.session_state:
    st.session_state["working_df"] = st.session_state["df"].copy()

working_df = st.session_state["working_df"]

# ====
# ① 値の編集(worst_value・best_valueを編集対象に変更)
# ====
st.subheader("値の編集")
st.caption("トルネードチャートの振れ幅(worst_value / best_value)を編集できます。")

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
editable_columns = ["node_id", "label", "worst_value", "best_value", "unit"]

edited_leaf_df = st.data_editor(
    working_df.loc[leaf_mask, editable_columns],
    disabled=["node_id", "label", "unit"],
    hide_index=True,
    key="tornado_value_editor",
)

working_df.loc[leaf_mask, ["worst_value", "best_value"]] = edited_leaf_df[["worst_value", "best_value"]].values
st.session_state["working_df"] = working_df

if st.button("元の値にリセット", key="tornado_reset"):
    st.session_state["working_df"] = st.session_state["df"].copy()
    st.rerun()

st.divider()

# ====
# ② ゴールシーク(収支が0になるよう、指定した項目だけを自動調整)
# ====
st.subheader("ゴールシーク(収支を0にする)")
st.caption("選んだ項目だけを動かして、収支がちょうど0になる値を自動探索します。他の項目は変更されません。")

leaf_options = working_df.loc[leaf_mask, ["node_id", "label"]]
label_to_id = dict(zip(leaf_options["label"], leaf_options["node_id"]))

selected_label = st.selectbox("収支を0にするために動かす項目", options=leaf_options["label"])

if st.button("ゴールシークを実行"):
    target_node_id = label_to_id[selected_label]
    solution, success = model_tree.goal_seek(working_df, target_node_id, target_root_value=0.0)

    if success:
        working_df.loc[working_df["node_id"] == target_node_id, "value"] = solution
        st.session_state["working_df"] = working_df
        st.success(f"「{selected_label}」を {solution:,.2f} に変更すると、収支が0になります")
        st.rerun()
    else:
        st.error(f"「{selected_label}」だけを動かしても、収支を0にできる値が見つかりませんでした")

st.divider()

# ====
# トルネードチャート本体
# ====
tornado_df, base_value = tornado.calc_tornado_data(working_df)

if len(tornado_df) == 0:
    st.warning("CSVに worst_value / best_value が設定されている末端項目がありません")
    st.stop()

fig = go.Figure()
fig.add_trace(go.Bar(
    y=tornado_df["label"],
    x=tornado_df["high"] - tornado_df["low"],
    base=tornado_df["low"],
    orientation="h",
    marker_color="#4C78A8",
    text=[f"{low:,.0f} 〜 {high:,.0f}" for low, high in zip(tornado_df["low"], tornado_df["high"])],
    textposition="outside",
))

fig.add_vline(x=base_value, line_dash="dash", line_color="gray")

fig.update_layout(
    title="各項目が収支に与える影響幅",
    xaxis_title="収支",
    yaxis_title="",
    height=100 + 45 * len(tornado_df),
    margin=dict(l=10, r=10, t=40, b=10),
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("数値一覧")
st.dataframe(
    tornado_df[["label", "low", "high", "impact"]].sort_values("impact", ascending=False),
    hide_index=True,
)
