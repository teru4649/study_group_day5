import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from modules import monte_carlo

st.title("モンテカルロシミュレーション")

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

working_df = st.session_state.get("working_df", st.session_state["df"])

st.subheader("分布パラメータの設定")
st.caption("各項目の distribution と param1〜3 を設定します。「自動入力してから保存」は worst_value・value・best_value から目安の値を計算し、まとめて保存します。")

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
leaf_ids = working_df.loc[leaf_mask, "node_id"].tolist()

dist_options = ["", "normal", "triangular", "uniform"]

# フォームの再構築版を管理する番号(保存・自動入力のたびに増やし、表示キャッシュを回避する)
if "param_form_version" not in st.session_state:
    st.session_state["param_form_version"] = 0

form_key = f"dist_param_form_v{st.session_state['param_form_version']}"

with st.form(form_key):
    new_values = {}

    for node_id in leaf_ids:
        row = working_df.loc[working_df["node_id"] == node_id].iloc[0]
        st.markdown(f"**{row['label']}**")

        cols = st.columns(4)
        current_dist = row.get("distribution") if pd.notna(row.get("distribution")) else ""
        dist_index = dist_options.index(current_dist) if current_dist in dist_options else 0

        with cols[0]:
            dist = st.selectbox(
                "分布", dist_options, index=dist_index,
                key=f"dist_{node_id}_{form_key}", label_visibility="collapsed"
            )
        with cols[1]:
            p1 = st.number_input(
                "param1", value=float(row["param1"]) if pd.notna(row.get("param1")) else 0.0,
                key=f"p1_{node_id}_{form_key}", label_visibility="collapsed"
            )
        with cols[2]:
            p2 = st.number_input(
                "param2", value=float(row["param2"]) if pd.notna(row.get("param2")) else 0.0,
                key=f"p2_{node_id}_{form_key}", label_visibility="collapsed"
            )
        with cols[3]:
            p3 = st.number_input(
                "param3", value=float(row["param3"]) if pd.notna(row.get("param3")) else 0.0,
                key=f"p3_{node_id}_{form_key}", label_visibility="collapsed"
            )

        new_values[node_id] = (dist, p1, p2, p3)

    col_a, col_b = st.columns(2)
    with col_a:
        submitted = st.form_submit_button("この内容で設定を保存")
    with col_b:
        auto_fill_clicked = st.form_submit_button("worst/value/bestから自動入力してから保存")

if submitted or auto_fill_clicked:
    # まず画面上で選ばれていた内容(distributionの選択)を反映
    for node_id, (dist, p1, p2, p3) in new_values.items():
        working_df.loc[working_df["node_id"] == node_id, "distribution"] = dist if dist != "" else np.nan
        working_df.loc[working_df["node_id"] == node_id, "param1"] = p1
        working_df.loc[working_df["node_id"] == node_id, "param2"] = p2
        working_df.loc[working_df["node_id"] == node_id, "param3"] = p3

    if auto_fill_clicked:
        # distributionが選ばれている項目だけ、param1〜3を自動計算で上書き
        for node_id in leaf_ids:
            row = working_df.loc[working_df["node_id"] == node_id].iloc[0]
            if pd.notna(row.get("distribution")) and row.get("distribution") != "":
                p1, p2, p3 = monte_carlo.auto_fill_params(row)
                if p1 is not None:
                    working_df.loc[working_df["node_id"] == node_id, "param1"] = p1
                    working_df.loc[working_df["node_id"] == node_id, "param2"] = p2
                    if p3 is not None:
                        working_df.loc[working_df["node_id"] == node_id, "param3"] = p3

    st.session_state["working_df"] = working_df
    st.session_state["param_form_version"] += 1  # 次回はフォームを新規ウィジェットとして再構築させる
    st.success("設定を保存しました")
    st.rerun()

st.divider()

n_trials = st.slider("試行回数", min_value=1000, max_value=50000, value=10000, step=1000)

if st.button("シミュレーションを実行"):
    results = monte_carlo.run_simulation(working_df, n_trials=n_trials)
    st.session_state["mc_results"] = results
    st.session_state["mc_n_trials"] = n_trials

if "mc_results" in st.session_state:
    results = st.session_state["mc_results"]

    # ====
    # ヒストグラム
    # ====
    st.subheader("収支の分布(ヒストグラム)")
    fig_hist = go.Figure(data=[go.Histogram(x=results, nbinsx=50, marker_color="#4C78A8")])
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="収支=0")
    fig_hist.update_layout(xaxis_title="収支", yaxis_title="回数", height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

    # ====
    # 累積確率曲線
    # ====
    st.subheader("累積確率曲線")
    sorted_results = np.sort(results)
    cum_prob = np.arange(1, len(sorted_results) + 1) / len(sorted_results)

    fig_cum = go.Figure(data=[go.Scatter(x=sorted_results, y=cum_prob, mode="lines", line_color="#4C78A8")])
    fig_cum.add_vline(x=0, line_dash="dash", line_color="red")
    fig_cum.update_layout(
        xaxis_title="収支",
        yaxis_title="累積確率(その値以下になる確率)",
        height=400,
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    prob_negative = (results < 0).mean()
    st.metric("収支が赤字(0未満)になる確率", f"{prob_negative * 100:.1f}%")

    # ====
    # 主要パーセンタイル表
    # ====
    st.subheader("主要パーセンタイル")
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    percentile_values = np.percentile(results, percentiles)
    percentile_df = pd.DataFrame({
        "パーセンタイル": [f"{p}%" for p in percentiles],
        "収支": [f"{v:,.0f}" for v in percentile_values],
    })
    st.dataframe(percentile_df, hide_index=True)

    st.caption(
        f"試行回数: {st.session_state['mc_n_trials']:,}回 / "
        f"平均: {results.mean():,.0f} / 標準偏差: {results.std():,.0f}"
    )
else:
    st.info("試行回数を設定し、「シミュレーションを実行」ボタンを押してください")
