import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules import breakeven

st.title("損益分岐点分析")
st.caption(
    "各項目について、他の値をすべて固定したまま、その項目だけを動かして収支がちょうど0になる値(損益分岐点)を計算します。"
    "「差分」は損益分岐点までの値の変化量、「安全余裕率」は現在値からの変化率です(プラスは増加方向、マイナスは減少方向に分岐点があることを示します)。"
)

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

working_df = st.session_state.get("working_df", st.session_state["df"])

breakeven_df, base_root_value = breakeven.calc_breakeven_table(working_df)

st.metric("現在の収支", f"{base_root_value:,.0f}")

if base_root_value < 0:
    st.warning("現在の設定では、既に収支が赤字です。表の「損益分岐点」は黒字転換に必要な値を示します。")

st.divider()

# ====
# 一覧表
# ====
st.subheader("損益分岐点 一覧")

display_df = breakeven_df.copy()
display_df["現在値"] = display_df.apply(
    lambda r: f"{r['現在値']:,.2f} {r['unit']}" if pd.notna(r["現在値"]) else "—", axis=1
)
display_df["損益分岐点"] = display_df.apply(
    lambda r: f"{r['損益分岐点']:,.2f} {r['unit']}" if pd.notna(r["損益分岐点"]) else "—", axis=1
)
display_df["差分"] = display_df.apply(
    lambda r: f"{r['差分']:+,.2f} {r['unit']}" if pd.notna(r["差分"]) else "—", axis=1
)
display_df["安全余裕率(%)"] = display_df["安全余裕率(%)"].apply(
    lambda v: f"{v:+.1f}%" if pd.notna(v) else "—"
)

st.dataframe(
    display_df[["label", "現在値", "損益分岐点", "差分", "安全余裕率(%)", "備考"]].rename(columns={"label": "項目"}),
    hide_index=True,
    use_container_width=True,
)

# ====
# 安全余裕率のグラフ(絶対値が小さい=リスクが高い項目ほど目立たせる)
# ====
chart_df = breakeven_df.dropna(subset=["安全余裕率(%)"]).copy()

if len(chart_df) > 0:
    chart_df["abs_margin"] = chart_df["安全余裕率(%)"].abs()
    chart_df = chart_df.sort_values("abs_margin")

    st.subheader("安全余裕率の比較(0に近いほど、少しの変化で赤字転落するリスクが高い項目)")

    colors = ["#D62728" if abs(v) < 10 else "#4C78A8" for v in chart_df["安全余裕率(%)"]]

    fig = go.Figure(data=[go.Bar(
        y=chart_df["label"],
        x=chart_df["安全余裕率(%)"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in chart_df["安全余裕率(%)"]],
        textposition="outside",
    )])
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        xaxis_title="安全余裕率(%)",
        yaxis_title="",
        height=100 + 40 * len(chart_df),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("赤色のバーは、安全余裕率が±10%以内(変化に対して特に脆弱)の項目です。")
else:
    st.info("損益分岐点を計算できた項目がありません(現在値が未設定、または分岐点が見つからない項目のみです)")
