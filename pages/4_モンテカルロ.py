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
st.caption(
    "1行につき「label,distribution,param1,param2,param3」の形式で入力してください。"
    "distributionが不要な項目(基準値のまま固定したい項目)は、その行を削除するか空欄にしてください。"
)

leaf_mask = working_df["operator"].isna() | (working_df["operator"] == "")
leaf_df = working_df.loc[leaf_mask, ["node_id", "label", "distribution", "param1", "param2", "param3"]]


def to_text_line(row) -> str:
    dist = row["distribution"] if pd.notna(row["distribution"]) else ""
    p1 = row["param1"] if pd.notna(row["param1"]) else ""
    p2 = row["param2"] if pd.notna(row["param2"]) else ""
    p3 = row["param3"] if pd.notna(row["param3"]) else ""
    return f"{row['label']},{dist},{p1},{p2},{p3}"


default_text = "\n".join(to_text_line(row) for _, row in leaf_df.iterrows())

# テキスト欄を「新しいウィジェット」として作り直すための番号
if "param_text_version" not in st.session_state:
    st.session_state["param_text_version"] = 0

if st.button("worst_value・value・best_value から自動入力した内容を下欄に反映"):
    lines = []
    for _, row in leaf_df.iterrows():
        full_row = working_df.loc[working_df["node_id"] == row["node_id"]].iloc[0]

        dist, p1, p2, p3 = monte_carlo.auto_fill_params(full_row)

        if dist is None:
            dist_str = row["distribution"] if pd.notna(row["distribution"]) else ""
            p1_str = "" if pd.isna(row["param1"]) else row["param1"]
            p2_str = "" if pd.isna(row["param2"]) else row["param2"]
            p3_str = "" if pd.isna(row["param3"]) else row["param3"]
        else:
            dist_str = dist
            p1_str = p1
            p2_str = p2
            p3_str = "" if p3 is None else p3

        lines.append(f"{row['label']},{dist_str},{p1_str},{p2_str},{p3_str}")

    st.session_state["param_text_prefill"] = "\n".join(lines)

    st.write("【デバッグ】生成されたlines:")
    st.write(lines)

    st.session_state["param_text_version"] += 1
    # st.rerun()  # ← 一時的にコメントアウト(デバッグ表示を確認するため)

text_value = st.session_state.get("param_text_prefill", default_text)
text_area_key = f"param_text_area_v{st.session_state['param_text_version']}"

param_text = st.text_area(
    "分布パラメータ一覧",
    value=text_value,
    height=250,
    key=text_area_key,
)

if st.button("この内容を保存"):
    label_to_id = dict(zip(leaf_df["label"], leaf_df["node_id"]))
    error_lines = []

    for line_no, line in enumerate(param_text.strip().split("\n"), start=1):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 5:
            error_lines.append(f"{line_no}行目: カンマ区切りが5項目になっていません → {line}")
            continue

        label, dist, p1, p2, p3 = parts
        if label not in label_to_id:
            error_lines.append(f"{line_no}行目: 「{label}」という項目名がCSVに見つかりません")
            continue

        node_id = label_to_id[label]
        working_df.loc[working_df["node_id"] == node_id, "distribution"] = dist if dist != "" else np.nan
        working_df.loc[working_df["node_id"] == node_id, "param1"] = float(p1) if p1 != "" else np.nan
        working_df.loc[working_df["node_id"] == node_id, "param2"] = float(p2) if p2 != "" else np.nan
        working_df.loc[working_df["node_id"] == node_id, "param3"] = float(p3) if p3 != "" else np.nan

    if error_lines:
        st.error("以下の行でエラーがありました:\n" + "\n".join(error_lines))
    else:
        st.session_state["working_df"] = working_df
        st.session_state.pop("param_text_prefill", None)
        st.session_state["param_text_version"] += 1  # 保存後も新しいウィジェットとして再表示させる
        st.success("分布パラメータを保存しました")
        st.rerun()

st.divider()

st.write("シミュレーション実行直前の distribution / param1〜3:")
st.write(working_df.loc[leaf_mask, ["label", "distribution", "param1", "param2", "param3"]])

n_trials = st.slider("試行回数", min_value=1000, max_value=50000, value=10000, step=1000)

if st.button("シミュレーションを実行"):
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
