###############################################################
#  app.py – FINAL CLEAN VERSION (Year System + Range Logic FIX)
###############################################################

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import altair as alt
import plotly.graph_objects as go
import plotly.express as px


# ------------------------------------------------------------
#  THEME COLORS
# ------------------------------------------------------------
COLOR_GREEN = "#C8F7C5"
COLOR_RED   = "#F7C5C5"
COLOR_GREY  = "#E0E0E0"
COLOR_GOLD  = "#C8A951"
COLOR_TEAL  = "#007E6D"

st.set_page_config(page_title="Dashboard KPI/KRI/KCI", layout="wide")


st.markdown(f"""
<style>
.main-title {{
    font-size: 36px;
    font-weight: bold;
    color: {COLOR_TEAL};
}}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>📊 Dashboard KPI / KRI / KCI</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
#  DATA FOLDER
# ------------------------------------------------------------
DATA_FOLDER = "data_tahun"
os.makedirs(DATA_FOLDER, exist_ok=True)

def get_file_path(tahun):
    return os.path.join(DATA_FOLDER, f"data_{tahun}.csv")

# ------------------------------------------------------------
#  INITIAL EMPTY DATA
# ------------------------------------------------------------
def init_data():
    return pd.DataFrame(columns=[
        "Jenis","Nama_Indikator","Kategori","Unit","Pemilik","Tanggal",
        "Target","Realisasi","Satuan","Keterangan",
        "Arah","Target_Min","Target_Max","Tahun"
    ])

# ------------------------------------------------------------
#  STATUS LOGIC
# ------------------------------------------------------------

def hitung_status(row):
    try:
        real = float(row["Realisasi"])
        target = float(row["Target"])
    except:
        return "N/A"

    # normalisasi
    arah = str(row.get("Arah", "")).strip().lower()

    if arah == "higher is better":
        return "Hijau" if real >= target else "Merah"

    if arah == "lower is better":
        return "Hijau" if real <= target else "Merah"

    if arah == "range":
        try:
            tmin = float(row["Target_Min"])
            tmax = float(row["Target_Max"])
            return "Hijau" if tmin <= real <= tmax else "Merah"
        except:
            return "N/A"

    return "N/A"

# ------------------------------------------------------------
#  SIDEBAR SELECT YEAR
# ------------------------------------------------------------
tahun_list = list(range(2024, 2032))
tahun_pilih = st.sidebar.selectbox("📅 Pilih Tahun Dataset", tahun_list, index=tahun_list.index(2025))

FILE_NAME = get_file_path(tahun_pilih)

# ------------------------------------------------------------
#  LOAD DATA
# ------------------------------------------------------------
if os.path.exists(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
else:
    df = init_data()

# Hapus baris-baris sampah / kosong
df = df[df["Nama_Indikator"].notna()]
df = df[df["Nama_Indikator"] != "nan"]
df = df[df["Nama_Indikator"] != ""]
df = df[df["Nama_Indikator"].str.strip() != ""]

# ====================================================
# HITUNG ULANG STATUS SETELAH LOAD CSV
# ====================================================
if len(df) > 0:
    df["Status"] = df.apply(hitung_status, axis=1)

# =====================================================
# NORMALISASI REALISASI TERHADAP TARGET (DALAM %)
# =====================================================
df["Skor_Normal"] = (df["Realisasi"].astype(float) / df["Target"].astype(float)) * 100
df["Skor_Normal"] = df["Skor_Normal"].round(2)

# ------------------------------------------------------------
#  INPUT FORM (VERSION FIXED)
# ------------------------------------------------------------
st.subheader("🧾 Input Indikator Baru")

c1, c2, c3 = st.columns(3)

with c1:
    jenis    = st.selectbox("Jenis", ["KPI", "KRI", "KCI"])
    kategori = st.text_input("Kategori")
    unit     = st.text_input("Unit")

with c2:
    nama     = st.text_input("Nama Indikator")
    pemilik  = st.text_input("Pemilik")
    tanggal  = st.date_input("Tanggal")

with c3:
    target    = st.number_input("Target", 0.0)
    realisasi = st.number_input("Realisasi", 0.0)
    satuan    = st.text_input("Satuan")

arah = st.selectbox(
    "Arah Penilaian",
    ["Higher is Better", "Lower is Better", "Range"]
)

tmin, tmax = None, None

# ----- DYNAMIC RANGE UI -----
if arah == "Range":
    st.markdown("### 🎯 Pengaturan Range Target")

    colr1, colr2 = st.columns(2)
    with colr1:
        tmin = st.number_input("Target Minimal", value=0.0)
    with colr2:
        tmax = st.number_input("Target Maksimal", value=0.0)

ket = st.text_area("Keterangan")

# ---- SUBMIT BUTTON ----
if st.button("➕ Tambah Indikator"):

    tahun_input = tanggal.year
    file_input  = get_file_path(tahun_input)

    new = pd.DataFrame([{
        "Jenis": jenis,
        "Nama_Indikator": nama,
        "Kategori": kategori,
        "Unit": unit,
        "Pemilik": pemilik,
        "Tanggal": tanggal.strftime("%Y-%m-%d"),
        "Target": target,
        "Realisasi": realisasi,
        "Satuan": satuan,
        "Keterangan": ket,
        "Arah": arah,
        "Target_Min": tmin,
        "Target_Max": tmax,
        "Tahun": tahun_input
    }])

    if os.path.exists(file_input):
        old = pd.read_csv(file_input)
        saved = pd.concat([old, new], ignore_index=True)
    else:
        saved = new

    saved.to_csv(file_input, index=False)
    st.success(f"Indikator berhasil ditambahkan ke tahun {tahun_input}!")

    st.rerun()  # << FIX PENTING

# ============================================================
#  DELETE & CLEAR DATA TAHUN INI (POSITION FIXED)
# ============================================================
st.subheader("🗑️ Hapus / Clear Data Tahun Ini")

if len(df) == 0:
    st.info("Belum ada data untuk tahun ini.")
else:

    # Buat kolom: 75% untuk dropdown + delete, 25% untuk clear
    col_del_left, col_del_right = st.columns([6, 2])

    # ---------------- LEFT SIDE (Dropdown + Hapus) ----------------
    with col_del_left:
        pilih_hapus = st.selectbox(
            "Pilih indikator untuk dihapus:",
            df["Nama_Indikator"].unique(),
            key="hapus_indikator"
        )

        if st.button("Hapus Indikator Ini"):
            df_new = df[df["Nama_Indikator"] != pilih_hapus]
            df_new.to_csv(FILE_NAME, index=False)
            st.success(f"Indikator '{pilih_hapus}' berhasil dihapus.")
            st.rerun()

    # ---------------- RIGHT SIDE (CLEAR BUTTON) ----------------
    with col_del_right:
        st.write("")  # memberi jarak vertikal agar tombol pas di baris yang sama
        st.write("")  # tambahan jarak
        if st.button("🧹 Clear Semua Data Tahun Ini"):
            kosong = init_data()
            kosong.to_csv(FILE_NAME, index=False)
            st.warning("SEMUA data tahun ini telah dihapus!")
            st.rerun()


# ------------------------------------------------------------
#  SIDEBAR SUMMARY
# ------------------------------------------------------------
st.sidebar.header("📊 Ringkasan Tahun Ini")

if len(df) > 0:
    total = len(df)
    hijau = (df["Status"] == "Hijau").sum()
    merah = (df["Status"] == "Merah").sum()
    na    = (df["Status"] == "N/A").sum()

    st.sidebar.metric("Total", total)
    st.sidebar.metric("Hijau", hijau)
    st.sidebar.metric("Merah", merah)
    st.sidebar.metric("N/A", na)

# ------------------------------------------------------------
#  HTML TABLE (COLORED)
# ------------------------------------------------------------
st.subheader("📋 Data (Colored)")

if len(df) > 0:

    html = "<table style='width:100%;border-collapse:collapse;'>"

    # header
    html += "<thead><tr>"
    for col in df.columns:
        html += f"<th style='border:1px solid #ccc;padding:6px;background:#eee;'>{col}</th>"
    html += "</tr></thead><tbody>"

    # rows
    for _, row in df.iterrows():
        status = row["Status"]
        if status == "Hijau": bg = COLOR_GREEN
        elif status == "Merah": bg = COLOR_RED
        else: bg = COLOR_GREY

        html += f"<tr style='background:{bg};'>"
        for col in df.columns:
            html += f"<td style='border:1px solid #ccc;padding:6px;'>{row[col]}</td>"
        html += "</tr>"

    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------
#  EXPORT CSV
# ------------------------------------------------------------
st.subheader("📤 Export CSV Tahun Ini")

if len(df) > 0:
    csv = df.to_csv(index=False).encode()
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"export_{tahun_pilih}.csv",
        mime="text/csv"
    )

# ============================================================
#   ✏️ EDIT LANGSUNG DI TABEL (INLINE EDIT)
# ============================================================

st.subheader("✏️ Edit Langsung di Tabel (Inline Edit)")

# Tampilkan editor
edited_df = st.data_editor(
    df,
    num_rows="dynamic",         # bisa tambah / delete row
    use_container_width=True,
    hide_index=False
)

# Tombol simpan perubahan
if st.button("💾 Simpan Perubahan Tabel"):
    edited_df.to_csv(FILE_NAME, index=False)
    st.success("Perubahan pada tabel berhasil disimpan!")
    st.rerun()



# ============================================================
#  📈 Combo Chart Profesional — Target vs Realisasi
# ============================================================
st.markdown("## 📊 KPI Dashboard")

# Ambil data indikator
df_bar = df.copy()

# Urutkan supaya output rapi
df_bar = df_bar.sort_values("Nama_Indikator")

# Buat 4 kolom
col1, col2, col3, col4 = st.columns(4, gap="large")

cols = [col1, col2, col3, col4]

# Loop semua indikator
for idx, (_, row) in enumerate(df_bar.iterrows()):
    col = cols[idx % 4]  # setiap 4 pindah baris ke bawah

    with col:
        st.markdown(f"##### **{row['Nama_Indikator']}**")
        st.caption(f"Unit: {row['Unit']} | Kategori: {row['Kategori']}")

        target = row['Target']
        real = row['Realisasi']
        capai = (real / target * 100) if target > 0 else 0

        st.markdown(f"""
        <span style='color:#d9534f; font-weight:bold;'>Capaian: {capai:.2f}%</span>
        """, unsafe_allow_html=True)

        # --- Mini Horizontal Bar ---
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=[real],
            y=["Realisasi"],
            orientation='h',
            marker=dict(color="#ff6b6b"),
            width=0.4
        ))

        fig.add_trace(go.Bar(
            x=[target],
            y=["Target"],
            orientation='h',
            marker=dict(color="#9aa0a6"),
            width=0.4
        ))

        fig.update_layout(
            height=130,
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=True, zeroline=False),
            yaxis=dict(showgrid=False)
        )

        st.plotly_chart(fig, use_container_width=True)




























































