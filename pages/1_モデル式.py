import streamlit as st
import streamlit.components.v1 as components
from modules import model_tree

st.title("モデル式(樹形図)")

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

# working_dfが無ければオリジナルから作成
if "working_df" not in st.session_state:
    st.session_state["working_df"] = st.session_state["df"].copy()

working_df = st.session_state["working_df"]

required_columns = ["node_id", "parent_id", "label", "operator", "value"]
missing_columns = [col for col in required_columns if col not in working_df.columns]
if missing_columns:
    st.error(f"CSVに必要な列が不足しています: {', '.join(missing_columns)}")
    st.stop()

# ====
# 値の編集UI(末端ノード=operatorが空の行のみ編集可能)
# ====
st.subheader("値の編集")
st.caption("末端の項目(演算子を持たない行)のみ値を変更できます。変更すると樹形図・各分析にすぐ反映されます。")

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
editable_columns = ["node_id", "label", "value", "unit"]

edited_leaf_df = st.data_editor(
    working_df.loc[leaf_mask, editable_columns],
    disabled=["node_id", "label", "unit"],  # valueだけ編集可能
    hide_index=True,
    key="value_editor",
)

# 編集結果を作業用データに反映
working_df.loc[leaf_mask, "value"] = edited_leaf_df["value"].values
st.session_state["working_df"] = working_df

if st.button("元の値にリセット"):
    st.session_state["working_df"] = st.session_state["df"].copy()
    st.rerun()

# ====
# 計算・表示(working_dfを使う)
# ====
try:
    result_df = model_tree.calc_all(working_df)
    root_id = model_tree.find_root_id(working_df)
    root_value = result_df.loc[result_df["node_id"] == root_id, "calculated_value"].iloc[0]

    st.metric(label="収支(ルートノード)の計算結果", value=f"{root_value:,.0f}")

    st.subheader("樹形図(マウスホイールで拡大縮小、ドラッグで移動できます)")
    tree_graph = model_tree.build_tree_graph(result_df)
    tree_html = model_tree.render_tree_html(tree_graph, height=600)
    components.html(tree_html, height=620, scrolling=True)

    st.session_state["result_df"] = result_df

except ValueError as e:
    st.error(f"モデル式の計算に失敗しました: {e}")
