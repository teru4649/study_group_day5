import streamlit as st
import plotly.graph_objects as go
from modules import tornado

st.title("トルネードチャート")

if "df" not in st.session_state:
    st.warning("トップページでCSVファイルをアップロードしてください")
    st.stop()

# 「モデル式」ページで値を編集していれば、その編集後の値を使う
df = st.session_state.get("working_df", st.session_state["df"])

tornado_df, base_value = tornado.calc_tornado_data(df)

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
