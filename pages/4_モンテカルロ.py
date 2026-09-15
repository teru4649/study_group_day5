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
st.caption("各項目の分布をプルダウンで選択してください。worst_value・best_valueが未入力の項目は「なし(基準値固定)」のみ選択できます。")

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
leaf_ids = working_df.loc[leaf_mask, "node_id"].tolist()

NO_DIST_LABEL = "なし(基準値固定)"
ALL_DIST_OPTIONS = [NO_DIST_LABEL, "normal", "triangular", "uniform"]

collected_rows = []  # 保存ボタン押下時に、この一覧をもとにworking_dfへ書き込む

for node_id in leaf_ids:
    row = working_df.loc[working_df["node_id"] == node_id].iloc[0]
    has_range = pd.notna(row.get("worst_value")) and pd.notna(row.get("best_value"))

    options = ALL_DIST_OPTIONS if has_range else [NO_DIST_LABEL]

    current_dist = row.get("distribution")
    if pd.isna(current_dist) or current_dist == "" or current_dist not in options:
        current_dist = NO_DIST_LABEL
    dist_index = options.index(current_dist)

    st.markdown(f"**{row['label']}**" + ("" if has_range else "(worst/best未入力のため分布は選べません)"))
    cols = st.columns(4)

    with cols[0]:
        dist_val = st.selectbox(
            "分布", options, index=dist_index,
            key=f"mc_dist_{node_id}", label_visibility="collapsed"
        )

    if dist_val == NO_DIST_LABEL:
        collected_rows.append((node_id, None, None, None, None))
        with cols[1]:
            st.caption("基準値で固定")
        continue

    # 分布が選ばれている場合、param1〜3の初期値を提案する
    # (working_dfに既存値があればそれを、無ければauto_fill_paramsで自動計算)
    row_for_default = row.copy()
    row_for_default["distribution"] = dist_val
    _, sugg_p1, sugg_p2, sugg_p3 = monte_carlo.auto_fill_params(row_for_default)

    default_p1 = row["param1"] if pd.notna(row.get("param1")) and row.get("distribution") == dist_val else sugg_p1
    default_p2 = row["param2"] if pd.notna(row.get("param2")) and row.get("distribution") == dist_val else sugg_p2
    default_p3 = row["param3"] if pd.notna(row.get("param3")) and row.get("distribution") == dist_val else sugg_p3

    # keyに分布の種類を含めることで、分布を切り替えた時だけ初期値が再提案される
    # (同じ分布のままなら、ユーザーが編集した値がそのまま保持される)
    with cols[1]:
        p1 = st.number_input(
            "param1", value=float(default_p1) if default_p1 is not None else 0.0,
            key=f"mc_p1_{node_id}_{dist_val}", label_visibility="collapsed"
        )
    with cols[2]:
        p2 = st.number_input(
            "param2", value=float(default_p2) if default_p2 is not None else 0.0,
            key=f"mc_p2_{node_id}_{dist_val}", label_visibility="collapsed"
        )

    p3 = None
    if dist_val == "triangular":
        with cols[3]:
            p3 = st.number_input(
                "param3", value=float(default_p3) if default_p3 is not None else 0.0,
                key=f"mc_p3_{node_id}_{dist_val}", label_visibility="collapsed"
            )
    else:
        with cols[3]:
            st.caption("(未使用)")

    collected_rows.append((node_id, dist_val, p1, p2, p3))

if st.button("この内容で分布設定を保存"):
    for node_id, dist_val, p1, p2, p3 in collected_rows:
        if dist_val is None:
            working_df.loc[working_df["node_id"] == node_id, "distribution"] = np.nan
            working_df.loc[working_df["node_id"] == node_id, ["param1", "param2", "param3"]] = np.nan
        else:
            working_df.loc[working_df["node_id"] == node_id, "distribution"] = dist_val
            working_df.loc[working_df["node_id"] == node_id, "param1"] = p1
            working_df.loc[working_df["node_id"] == node_id, "param2"] = p2
            working_df.loc[working_df["node_id"] == node_id, "param3"] = p3 if p3 is not None else np.nan

    st.session_state["working_df"] = working_df
    st.success("分布パラメータを保存しました")
    st.rerun()

st.divider()

st.write("シミュレーション実行直前の distribution / param1〜3:")
st.write(
    working_df.loc[
        leaf_mask,
        ["label", "worst_value", "best_value", "distribution", "param1", "param2", "param3"],
    ]
)

n_trials = st.slider("試行回数", min_value=1000, max_value=50000, value=10000, step=1000)

if st.button("シミュレーションを実行"):
    st.write("【デバッグ】計算直前のworking_df:")
    st.write(working_df.loc[leaf_mask, ["label", "distribution", "param1", "param2", "param3"]])
    results = monte_carlo.run_simulation(working_df, n_trials=n_trials)
    st.session_state["mc_results"] = results
    st.session_state["mc_n_trials"] = n_trials

if "mc_results" in st.session_state:
    results = st.session_state["mc_results"]

    st.subheader("収支の分布(ヒストグラム)")
    fig_hist = go.Figure(data=[go.Histogram(x=results, nbinsx=50, marker_color="#4C78A8")])
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="収支=0")
    fig_hist.update_layout(xaxis_title="収支", yaxis_title="回数", height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

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
