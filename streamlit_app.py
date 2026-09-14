import streamlit as st
import pandas as pd

# ====
# パスワード認証
# ====
def check_password():
    "パスワードが正しければTrueを返す"

    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # パスワードをメモリから消す処理
        else:
            st.session_state["password_correct"] = False  # 不一致時の処理

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "パスワードを入力してください",
        type="password",
        on_change=password_entered,
        key="password"
    )
    if "password_correct" in st.session_state:
        st.error("パスワードが違います")
    return False

if not check_password():
    st.stop()

# ====
# ここから本体(認証後のみ実行)
# 全ページ共通の要素(ファイルアップロード)をここに置く
# ====

st.title("感度分析・期待値計算ツール")

uploaded_file = st.file_uploader(
    "分析対象のCSVファイルをアップロードしてください",
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state["df"] = df                # オリジナル(変更不可の基準値)
        st.session_state["working_df"] = df.copy()  # 編集用の作業コピー
        st.write("⚠️ working_dfがリセットされました(この行が出るたびに要注意)")
        st.success(f"読み込み完了:{df.shape[0]}行 × {df.shape[1]}列")
        st.dataframe(df)
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました:{e}")
elif "df" not in st.session_state:
    st.info("csvファイルをアップロードすると内容が表示されます")

# ====
# ページ定義・ナビゲーション
# ====

model_tree_page = st.Page("pages/1_モデル式.py", title="モデル式", icon=":material/schema:")
tornado_page = st.Page("pages/2_トルネードチャート.py", title="トルネードチャート", icon=":material/bar_chart:")
sensitivity_page = st.Page("pages/3_感度分析.py", title="感度分析", icon=":material/tune:")
monte_carlo_page = st.Page("pages/4_モンテカルロ.py", title="モンテカルロ", icon=":material/casino:")
breakeven_page = st.Page("pages/5_損益分岐点分析.py", title="損益分岐点分析", icon=":material/trending_up:")

pg = st.navigation([
    model_tree_page,
    tornado_page,
    sensitivity_page,
    monte_carlo_page,
    breakeven_page,
])
pg.run()
