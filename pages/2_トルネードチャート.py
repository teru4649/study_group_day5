import streamlit as st
import plotly.graph_objects as go
from modules import tornado, model_tree

st.title("トルネードチャート")

# ---デバッグ用(原因切り分けのため一時的に追加)---
st.write("現在のworking_df(worst_value/best_value):")
st.write(st.session_state.get("working_df", "working_dfがまだありません")[["label", "worst_value", "best_value"]] if "working_df" in st.session_state else "未設定")
# ---ここまで---

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

if "working_df" not in st.session_state:
    st.session_state["working_df"] = st.session_state["df"].copy()

working_df = st.session_state["working_df"]

# ゴールシーク実行直後(rerun後)にメッセージを表示するための処理
if "goal_seek_message" in st.session_state:
    kind, msg = st.session_state.pop("goal_seek_message")
    if kind == "success":
        st.success(msg)
    else:
        st.error(msg)

# ====
# ① 値の編集(worst_value・best_valueを編集対象に変更)
# ====
st.subheader("値の編集")
st.caption("トルネードチャートの振れ幅(worst_value / best_value)を編集できます。")

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
editable_columns = ["node_id", "label", "worst_value", "best_value", "unit"]

editor_key = "tornado_value_editor"

# 編集欄には、末端ノードだけを連番インデックスで渡す
leaf_view = working_df.loc[leaf_mask, editable_columns].reset_index(drop=True)
# 連番インデックス → working_df上の実際の行番号 の対応表
leaf_index_map = working_df.index[leaf_mask].tolist()

st.data_editor(
    leaf_view,
    disabled=["node_id", "label", "unit"],
    hide_index=True,
    key=editor_key,
)

# 実際に編集操作があった行・列だけをworking_dfに書き戻す
editor_state = st.session_state.get(editor_key, {})
edited_rows = editor_state.get("edited_rows", {})

if edited_rows:
    for row_position, changes in edited_rows.items():
        actual_index = leaf_index_map[int(row_position)]
        for column_name, new_value in changes.items():
            if column_name in ["worst_value", "best_value"]:
                working_df.loc[actual_index, column_name] = new_value
    st.session_state["working_df"] = working_df

if st.button("元の値にリセット", key="tornado_reset"):
    st.session_state["working_df"] = st.session_state["df"].copy()
    if editor_key in st.session_state:
        del st.session_state[editor_key]
    st.rerun()

st.divider()

# ====
# ② ゴールシーク(収支を0にするworst_value/best_valueを逆算)
# ====
st.subheader("ゴールシーク(収支を0にする)")
st.caption("選んだ項目の worst_value または best_value を、収支がちょうど0になる値として逆算します。他の値は変更されません。")

leaf_options = working_df.loc[leaf_mask, ["node_id", "label"]]
label_to_id = dict(zip(leaf_options["label"], leaf_options["node_id"]))

col1, col2 = st.columns(2)
with col1:
    selected_label = st.selectbox("対象の項目", options=leaf_options["label"])
with col2:
    target_column = st.radio("逆算する対象", options=["worst_value", "best_value"], horizontal=True)

if st.button("ゴールシークを実行"):
    target_node_id = label_to_id[selected_label]
    before_value = working_df.loc[working_df["node_id"] == target_node_id, target_column].iloc[0]

    solution, success = model_tree.goal_seek(working_df, target_node_id, target_root_value=0.0)

        if success:
        working_df.loc[working_df["node_id"] == target_node_id, target_column] = solution
        st.session_state["working_df"] = working_df

        # 編集欄が持っている古い差分情報を消す(これが残っていると次回上書きされるため)
        if editor_key in st.session_state:
            del st.session_state[editor_key]

        st.session_state["goal_seek_message"] = (
            "success",
            f"「{selected_label}」の {target_column} を "
            f"{before_value:,.2f} → {solution:,.2f} に変更すると、収支が0になります"
        )
    else:
        st.session_state["goal_seek_message"] = (
            "error",
            f"「{selected_label}」の {target_column} だけを動かしても、収支を0にできる値が見つかりませんでした"
        )

    st.rerun()

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
