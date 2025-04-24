import streamlit as st
import pandas as pd
import json
import os
import glob

st.set_page_config(page_title="Dataset Mapper", layout="wide")
st.title("🧬 Dataset Matrixian to Altum Mapper")

# Default file paths
default_a_path = "data/a_data_altum_big.json"
default_b_path = "data/b_data_matrixian_big.json"
mapping_folder = "mappings"
os.makedirs(mapping_folder, exist_ok=True)

# --- File Loaders ---
def load_uploaded_or_default(uploaded_file, fallback_path):
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".json"):
            return pd.json_normalize(json.load(uploaded_file))
        else:
            return pd.read_csv(uploaded_file)
    elif os.path.exists(fallback_path):
        with open(fallback_path, "r", encoding="utf-8") as f:
            if fallback_path.endswith(".json"):
                return pd.json_normalize(json.load(f))
            else:
                return pd.read_csv(f)
    return pd.DataFrame()

# --- Sidebar Uploads ---
st.sidebar.header("📂 Load Files or Mappings")
file_a = st.sidebar.file_uploader("Upload Dataset A, Altum (optional)", type=["json", "csv"])
file_b = st.sidebar.file_uploader("Upload Dataset M, Matrixian (optional)", type=["json", "csv"])

existing_mappings = glob.glob(f"{mapping_folder}/*.json")
mapping_options = [""] + existing_mappings
default_index = 1 if len(mapping_options) > 1 else 0

selected_mapping_path = st.sidebar.selectbox(
    "Or choose saved mapping", 
    mapping_options, 
    index=default_index
)

loaded_mapping = {}

if selected_mapping_path:
    try:
        with open(selected_mapping_path, "r") as f:
            loaded_mapping = json.load(f)
        st.sidebar.success(f"Loaded mapping: {os.path.basename(selected_mapping_path)}")
    except Exception as e:
        st.sidebar.error(f"Failed to load mapping: {e}")

uploaded_mapping_file = st.sidebar.file_uploader("Upload Mapping JSON (optional)", type=["json"])
if uploaded_mapping_file:
    try:
        loaded_mapping = json.load(uploaded_mapping_file)
        st.sidebar.success("Uploaded mapping loaded.")
    except Exception as e:
        st.sidebar.error(f"Invalid mapping file: {e}")

# --- Load Data ---
df_a = load_uploaded_or_default(file_a, default_a_path)
df_b = load_uploaded_or_default(file_b, default_b_path)

if df_a.empty or df_b.empty:
    st.warning("Waiting for data... Please upload files or check default paths.")
    st.stop()

# --- Field Mapping ---
st.subheader("📋 Map Dataset A Fields to Dataset B (multi-select allowed with suggestions)")
mapping = {}

for col in df_a.columns:
    default_b_cols = loaded_mapping.get(col)
    if not default_b_cols:
        if col in df_b.columns:
            default_b_cols = [col]
        else:
            default_b_cols = []
    if isinstance(default_b_cols, str):
        default_b_cols = [default_b_cols]

    selected_b_cols = st.multiselect(
        f"Map A field `{col}` to one or more M fields:",
        options=list(df_b.columns),
        default=default_b_cols,
        key=col
    )
    if selected_b_cols:
        mapping[col] = selected_b_cols

# --- Preview Table ---
if mapping:
    st.subheader("🔍 Preview Comparison (First 30 Rows)")

    preview = pd.DataFrame()
    min_len = min(len(df_a), len(df_b))

    for a_col, b_fields in mapping.items():
        a_series = (
            df_a[a_col]
            .iloc[:min_len]
            .astype(str)
            .reset_index(drop=True)
        )

        b_combined = (
            df_b[b_fields[0]]
            .iloc[:min_len]
            .astype(str)
            .reset_index(drop=True)
        )

        for extra_field in b_fields[1:]:
            next_series = (
                df_b[extra_field]
                .iloc[:min_len]
                .astype(str)
                .reset_index(drop=True)
            )
            b_combined += " | " + next_series

        preview[f"A: {a_col}"] = a_series
        preview[f"M: {', '.join(b_fields)}"] = b_combined
        preview[f"Match: {a_col}"] = a_series == b_combined

    if preview.empty:
        st.warning("⚠️ All preview columns are empty. Try adjusting the mappings or uploading different files.")
    else:
        st.dataframe(preview.head(400), use_container_width=True, height=800)

    # --- Download/Save Mapping ---
    st.download_button(
        label="⬇️ Download Mapping as JSON",
        data=json.dumps(mapping, indent=2),
        file_name="column_mapping.json",
        mime="application/json"
    )

    save_name = st.text_input("📁 Save this mapping as (e.g. `altum_matrixian.json`):")
    if save_name and st.button("💾 Save Mapping"):
        save_path = os.path.join(mapping_folder, save_name)
        with open(save_path, "w") as f:
            json.dump(mapping, f, indent=2)
        st.success(f"Mapping saved to {save_path}")
