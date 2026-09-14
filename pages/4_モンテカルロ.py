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
