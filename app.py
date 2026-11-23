import json
import re
from io import StringIO

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Copy Object → CSV", page_icon="📄", layout="wide")
st.title("Copy Object → CSV")
st.caption("Paste hasil Copy object dari Console, atau upload file .json / .txt.")


def parse_raw(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # "Copy object" dari Console kadang menghasilkan format JS
        # (key tanpa tanda kutip, single quote, trailing comma).
        t = re.sub(r",\s*([}\]])", r"\1", text)  # hapus trailing comma
        t = re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', t)  # key tanpa kutip
        t = t.replace("'", '"')
        t = t.replace("undefined", "null")
        return json.loads(t)


def find_records(obj):
    """Cari list of dict terbesar di dalam JSON bersarang."""
    best = []

    def walk(o):
        nonlocal best
        if isinstance(o, list):
            if o and all(isinstance(i, dict) for i in o) and len(o) > len(best):
                best = o
            for i in o:
                walk(i)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)

    walk(obj)
    return best


def to_records(data):
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, dict):
        return find_records(data) or [data]
    if isinstance(data, list):
        return [{"value": v} for v in data]
    return [{"value": data}]


col_paste, col_upload = st.columns(2)

with col_paste:
    pasted = st.text_area(
        "Paste Copy object",
        height=220,
        placeholder='[{"id": 1, "name": "contoh"}, ...]',
    )

with col_upload:
    uploaded = st.file_uploader("Atau upload file .json / .txt", type=["json", "txt"])

filename = st.text_input("Nama file CSV", value="output.csv")
if filename and not filename.lower().endswith(".csv"):
    filename = f"{filename}.csv"

raw = None
if uploaded is not None:
    raw = uploaded.read().decode("utf-8")
elif pasted and pasted.strip():
    raw = pasted

if st.button("Convert ke CSV", type="primary", disabled=not raw):
    try:
        data = parse_raw(raw)
        records = to_records(data)
        df = pd.json_normalize(records, sep=".")

        st.success(f"Jumlah baris: {len(df)}, kolom: {len(df.columns)}")
        st.dataframe(df, use_container_width=True)

        csv_buf = StringIO()
        df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="Download CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=filename,
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Gagal parse data: {e}")
elif not raw:
    st.info("Paste teks atau upload file terlebih dahulu.")
