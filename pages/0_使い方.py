import streamlit as st
import streamlit.components.v1 as components
 
st.title("使い方(操作マニュアル)")
 
st.caption(
    "このページでは、感度分析・期待値計算ツールの使い方をまとめたマニュアルを表示しています。"
    "別ウィンドウで開きたい場合は、下の枠内を右クリックして「フレームだけを開く」なども利用できます。"
)
 
manual_path = "manual/操作マニュアル.html"
 
try:
    with open(manual_path, encoding="utf-8") as f:
        manual_html = f.read()
    components.html(manual_html, height=1000, scrolling=True)
except FileNotFoundError:
    st.error(
        f"マニュアルファイルが見つかりません({manual_path})。"
        "リポジトリに manual/操作マニュアル.html が含まれているか確認してください。"
    )
