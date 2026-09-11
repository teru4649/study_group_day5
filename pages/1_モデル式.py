import streamlit as st
from modules import model_tree

st.title("モデル式(樹形図)")

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

df = st.session_state["df"]

# CSVに必須列が揃っているか事前チェック
required_columns = ["node_id", "parent_id", "label", "operator", "value"]
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    st.error(f"CSVに必要な列が不足しています: {', '.join(missing_columns)}")
    st.stop()

try:
    result_df = model_tree.calc_all(df)
    root_id = model_tree.find_root_id(df)
    root_value = result_df.loc[result_df["node_id"] == root_id, "calculated_value"].iloc[0]

    st.metric(label="収支(ルートノード)の計算結果", value=f"{root_value:,.0f}")

    st.subheader("全ノードの計算結果")
    st.dataframe(
        result_df[["node_id", "parent_id", "label", "operator", "value", "calculated_value"]]
    )

    st.subheader("樹形図")
    tree_graph = model_tree.build_tree_graph(result_df)
    st.graphviz_chart(tree_graph, use_container_width=True)

    # 後続ページ(トルネードチャート等)でも使えるよう保存
    st.session_state["result_df"] = result_df

except ValueError as e:
    st.error(f"モデル式の計算に失敗しました: {e}")
