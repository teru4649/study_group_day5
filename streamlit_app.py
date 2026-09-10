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
    del st.session_state["password"] # パスワードをメモリから消す処理
  else:
    st.session_state["password_correct"] = False #不一致時の処理

# 既に認証済みならスキップ
if st.session_state.get("password_correct",False):
  return True

# パスワード入力欄を表示
st.text_input(
  "パスワードを入力してください",
  type="password",
  on_change=password_entered,
  key="password")

# 一度入力して間違っていた場合のみエラー表示
if "password_correct" in st.session_state:
  st.error("パスワードが違います")

return False

# 認証が通らないと以降の処理に進めない
if not check_password():
  st.stop()

# ====
# ここから本体で認証後のみ実行。
# ====

st.title("感度分析・期待値計算ツール")

uploaded_file = st.file_uploader(
  "分析対象のCSVファイルをアップロードしてください",
  type=["csv"])

if uploaded_file is not None:
  try:
    df = pd.read_csv(uploaded_file)
    st.success(f"読み込み完了:{df.shape[0]}行 × {df.shapre[1]}列")
    st.dataframe(df)
  except Exception as e:
    st.error(f"ファイルの読み込みに失敗しました:{e}")
else:
  st.info("csvファイルをアップロードすると内容が表示されます")
