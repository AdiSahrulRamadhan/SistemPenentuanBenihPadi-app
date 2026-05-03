import streamlit as st
import pandas as pd
import time
import numpy as np
import sqlite3
import json
from streamlit_option_menu import option_menu

# =========================
# DATABASE
# =========================

DB_PATH = "database.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS app_data (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def save_db(key, value):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO app_data (key, value)
    VALUES (?, ?)
    """, (key, json.dumps(value)))

    conn.commit()
    conn.close()

def load_db(key):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT value FROM app_data WHERE key=?", (key,))
    result = c.fetchone()

    conn.close()

    if result:
        return json.loads(result[0])
    return None

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

# =========================
# AUTO DETECT SEPARATOR
# =========================
def load_data(file):
    try:
        return pd.read_csv(file, sep=None, engine='python')
    except:
        try:
            return pd.read_csv(file, sep=';')
        except:
            return pd.read_csv(file)

# =========================
# CSS
# =========================
st.markdown("""
<style>
[data-testid="stSidebar"] {background-color: #2c3e50;}
.sidebar-title {text-align: center; color: white; font-size: 18px; font-weight: bold;}
.logo {text-align: center; font-size: 60px;}
[data-testid="stSidebar"] span {color: white !important;}
[data-testid="stSidebar"] li:hover {background-color: #34495e !important; border-radius: 8px;}
[data-testid="stSidebar"] li[data-selected="true"] {background-color: #1abc9c !important; border-radius: 8px;}

.blue-btn button {
    background-color: #3498db !important;
    color: white !important;
    border-radius: 8px;
    padding: 10px;
    font-weight: bold;
}
.blue-btn button:hover {
    background-color: #2980b9 !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
if "menu" not in st.session_state:
    st.session_state.menu = "Upload Data"

with st.sidebar:

    st.markdown("""
    <div class='sidebar-title'>
        SISTEM PENENTUAN<br>
        VARIETAS BENIH PADI
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='logo'>🌾</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=["Upload Data","Preprocessing","Pembobotan","Perangkingan","Evaluasi"],
        icons=["upload","gear","bar-chart","list","check-circle"],
        default_index=[
            "Upload Data","Preprocessing","Pembobotan","Perangkingan","Evaluasi"
        ].index(st.session_state.menu),
    )

st.session_state.menu = selected

# =========================
# LOAD DATA DARI DATABASE
# =========================
data_db = load_db("data_awal")

if data_db:
    try:
        st.session_state.data = pd.DataFrame(data_db)
    except:
        st.session_state.data = None
else:
    st.session_state.data = None

# =========================
# LOAD PREPROCESSING
# =========================
pre = load_db("preprocess")
if pre:
    st.session_state.data_preprocessed = pd.DataFrame(pre)

# =========================
# LOAD CONFIG
# =========================
config = load_db("config")
if config:
    st.session_state.drop_cols = config.get("drop_cols", [])
    st.session_state.kriteria = config.get("kriteria", [])
    st.session_state.alternatif = config.get("alternatif", None)
    st.session_state.sub_config = config.get("sub_config", {})
    st.session_state.mapping_kriteria = config.get("mapping_kriteria", {})
    st.session_state.ahp_matrix = config.get("ahp_matrix", None)

# =========================
# LOAD BOBOT
# =========================
bobot = load_db("bobot")
if bobot:
    st.session_state.bobot_ahp = pd.Series(bobot.get("ahp", {}))
    st.session_state.bobot_fuzzy = pd.Series(bobot.get("fuzzy", {}))

# =========================
# LOAD SKENARIO
# =========================
skenario = load_db("skenario")
if skenario:
    st.session_state.skenario_list = skenario

# =========================
# MENU UPLOAD
# =========================
if selected == "Upload Data":

    st.title("Upload Dataset")

    file = st.file_uploader("Upload file (CSV / Excel)", type=["csv","xlsx"])

    st.caption("""
📌 Upload terbaru akan menggantikan data lama.
Mendukung CSV & Excel dan auto separator.
""")

    if file is not None:

        try:
            # =========================
            # VALIDASI NAMA FILE
            # =========================
            if not (file.name.endswith(".csv") or file.name.endswith(".xlsx")):
                st.error("❌ Format file tidak didukung! Gunakan CSV atau Excel (.xlsx)")
                st.stop()

            # =========================
            # CEK FILE SAMA / TIDAK
            # =========================
            last_file = load_db("filename")
            is_new_file = file.name != last_file

            # =========================
            # LOAD FILE
            # =========================
            try:
                if file.name.endswith(".csv"):
                    df = load_data(file)
                else:
                    df = pd.read_excel(file)
            except Exception:
                notif = st.empty()
                notif.error("❌ File gagal dibaca! Pastikan format benar.")
                time.sleep(4)
                notif.empty()
                st.stop()

            # =========================
            # VALIDASI DATA KOSONG
            # =========================
            if df is None or df.empty:
                notif = st.empty()
                notif.warning("⚠️ File kosong!")
                time.sleep(4)
                notif.empty()
                st.stop()

            # =========================
            # VALIDASI KOLOM MINIMAL
            # =========================
            if df.shape[1] < 2:
                st.error("❌ Data minimal harus memiliki 2 kolom!")
                st.stop()

            # =========================
            # SIMPAN KE DATABASE
            # =========================
            save_db("data_awal", df.to_dict())
            save_db("filename", file.name)

            # =========================
            # UPDATE SESSION
            # =========================
            st.session_state.data = df

            # =========================
            # RESET HANYA JIKA FILE BARU
            # =========================
            if is_new_file:

                # reset DB turunan
                save_db("preprocess", None)
                save_db("config", None)
                save_db("bobot", None)
                save_db("skenario", None)

                # 🔥 reset semua session terkait
                keys_to_reset = [
                    "data_preprocessed",
                    "skenario_list",
                    "data_edit",
                    "kriteria",
                    "alternatif",
                    "sub_config",
                    "mapping_kriteria",
                    "ahp_matrix",
                    "bobot_ahp",
                    "bobot_fuzzy"
                ]

                for k in keys_to_reset:
                    st.session_state.pop(k, None)

            # =========================
            # NOTIFIKASI SUKSES
            # =========================
            notif = st.empty()
            if is_new_file:
                notif.success("✅ Upload berhasil! Data baru siap diproses.")
            else:
                notif.info("ℹ️ File sama diupload kembali, data tidak direset.")

            time.sleep(4)
            notif.empty()

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan saat upload: {e}")


    # =========================
    # TAMPILKAN DATA
    # =========================
    if st.session_state.data is not None:

        df = st.session_state.data

        last_file = load_db("filename") or "-"

        st.info(f"Dataset aktif: {last_file}")

        col1,col2 = st.columns(2)
        col1.info(f"Jumlah Data: {df.shape[0]}")
        col2.info(f"Jumlah Variabel: {df.shape[1]}")

        st.subheader("Tipe Data Variabel")
        st.dataframe(pd.DataFrame({
            "Variabel": df.columns,
            "Tipe": df.dtypes.astype(str)
        }), use_container_width=True)

        st.subheader("Preview Data")
        st.dataframe(df, use_container_width=True)

        colA,colB,colC = st.columns([6,1,2])
        with colC:
            st.markdown('<div class="blue-btn">', unsafe_allow_html=True)
            if st.button("➡️ Preprocessing Data"):
                st.session_state.menu = "Preprocessing"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# =========================
# MENU PREPROCESSING
# =========================

elif selected == "Preprocessing":

    st.title("Preprocessing Data")

    df = st.session_state.data

    if df is None:
        st.warning("Upload data dulu")
    else:

        # =========================
        # LOAD DATA PREPROCESS DARI DB
        # =========================
        pre_db = load_db("preprocess")
        if pre_db:
            st.session_state.data_preprocessed = pd.DataFrame(pre_db)

        # 🔥 tampilkan jika sudah pernah disimpan
        if "data_preprocessed" in st.session_state:
            st.info("📌 Menggunakan hasil preprocessing tersimpan")
            st.dataframe(st.session_state.data_preprocessed)
        # =========================
        # 🔥 LOAD DATA TERBARU DARI DB
        # =========================
        data_db = load_db("data_awal")

        if data_db:
            df = pd.DataFrame(data_db)
            st.session_state.data = df
        else:
            st.warning("⚠️ Data belum tersedia, silakan upload dulu")

        # =========================
        # 🔥 DATA AWAL (FULL EDIT MODE)
        # =========================
        st.subheader("📊 Data Awal")

        st.markdown("""
        ### 📝 Penjelasan:
        Data dapat diedit langsung pada tabel seperti Excel.

        ### Fitur:
        - Edit semua nilai (numerik / string)
        - Tambah baris otomatis
        - Tambah variabel (kolom)
        - Simpan perubahan ke database

        ### Ketentuan:
        - Data tidak boleh kosong
        - Kolom tidak boleh duplikat
        - Jika numerik kosong → otomatis 0
        - Jika string kosong → tetap kosong ("")
        - Jumlah data mengikuti dataset utama
        """)

        # =========================
        # LOAD DATA TERBARU
        # =========================
        data_db = load_db("data_awal")

        if data_db:
            df = pd.DataFrame(data_db)
            st.session_state.data = df
        else:
            df = st.session_state.data

        # =========================
        # INIT SESSION EDIT
        # =========================
        if "data_edit" not in st.session_state:
            st.session_state.data_edit = df.copy()

        # =========================
        # 🔥 TABEL EDIT UTAMA
        # =========================
        df_edit = st.data_editor(
            st.session_state.data_edit,
            use_container_width=True,
            num_rows="dynamic",  # bisa tambah row
            key="main_editor"
        )

        # simpan ke session
        st.session_state.data_edit = df_edit

        # =========================
        # 🔥 INFO DATA
        # =========================
        col1, col2 = st.columns(2)
        col1.info(f"Jumlah Baris: {df_edit.shape[0]}")
        col2.info(f"Jumlah Kolom: {df_edit.shape[1]}")

        # =========================
        # 🔥 TOMBOL SIMPAN (POSISI DI SINI SESUAI PERMINTAAN)
        # =========================
        st.markdown("""
        **Penjelasan:**
        Klik tombol ini untuk menyimpan semua perubahan pada tabel.

        **Kondisi:**
        - Semua perubahan akan menggantikan data lama
        - Data akan disimpan ke database
        - Pastikan tidak ada error sebelum menyimpan
        """)

        if st.button("💾 Simpan Perubahan Data"):

            try:
                df_save = st.session_state.data_edit.copy()

                # =========================
                # VALIDASI
                # =========================
                if df_save.empty:
                    st.error("❌ Data tidak boleh kosong!")
                    st.stop()

                # cek kolom duplikat
                if df_save.columns.duplicated().any():
                    st.error("❌ Terdapat nama kolom duplikat!")
                    st.stop()

                # =========================
                # HANDLE DATA KOSONG
                # =========================
                for col in df_save.columns:

                    if df_save[col].dtype == object:
                        df_save[col] = df_save[col].fillna("")
                    else:
                        df_save[col] = pd.to_numeric(df_save[col], errors='coerce').fillna(0)

                # =========================
                # SIMPAN KE DB
                # =========================
                save_db("data_awal", df_save.to_dict())

                st.session_state.data = df_save

                notif = st.empty()
                notif.success("✅ Perubahan data berhasil disimpan!")

                time.sleep(3)
                notif.empty()

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {e}")

        # =========================
        # 🔥 TAMBAH VARIABEL (SETELAH SIMPAN)
        # =========================
        st.markdown("---")
        st.subheader("➕ Tambah Variabel Baru")

        st.markdown("""
        **Penjelasan:**
        Menambahkan kolom baru ke dataset.

        **Kondisi:**
        - Nama variabel harus unik
        - Nilai default akan diisi otomatis
        """)

        col1, col2 = st.columns(2)

        nama_kolom = col1.text_input("Nama Variabel Baru")
        tipe_data = col2.selectbox("Tipe Data", ["Numerik", "String"])

        if st.button("➕ Tambahkan Kolom"):

            if not nama_kolom:
                st.error("❌ Nama variabel harus diisi!")
            else:
                df_temp = st.session_state.data_edit

                if nama_kolom in df_temp.columns:
                    st.error("❌ Kolom sudah ada!")
                else:
                    if tipe_data == "Numerik":
                        df_temp[nama_kolom] = 0
                    else:
                        df_temp[nama_kolom] = ""

                    st.session_state.data_edit = df_temp

                    notif = st.empty()
                    notif.success("✅ Kolom berhasil ditambahkan!")

                    time.sleep(2)
                    notif.empty()

                    st.rerun()

        # =========================
        # 1️⃣ HAPUS FITUR
        # =========================
        st.subheader("1️⃣ Hapus Fitur")

        st.markdown("""
**Penjelasan:**
Tahap ini digunakan untuk menghapus kolom yang tidak diperlukan dalam proses pengambilan keputusan.

**Tujuan:**
Mengurangi noise dan fokus hanya pada kriteria penting.

**Contoh:**
Kolom seperti ID, Nama, atau Timestamp biasanya tidak digunakan sebagai kriteria.
""")

        default_drop = st.session_state.get("drop_cols", [])
        default_drop = [c for c in default_drop if c in df.columns]

        drop_cols = st.multiselect(
            "Pilih kolom yang dihapus",
            df.columns,
            default=default_drop
        )

        df_clean = df.drop(columns=drop_cols)

        st.dataframe(df_clean, use_container_width=True)

        # =========================
        # 2️⃣ PILIH KRITERIA
        # =========================
        st.subheader("2️⃣ Pilih Kriteria")

        st.markdown("""
**Penjelasan:**
Kriteria adalah variabel yang digunakan dalam proses penilaian.

**Tujuan:**
Menentukan faktor yang mempengaruhi keputusan.

**Contoh:**
Produktivitas, Harga, Ketahanan, dll.
""")

        default_kriteria = st.session_state.get("kriteria", [])
        default_kriteria = [k for k in default_kriteria if k in df_clean.columns]

        kriteria = st.multiselect(
            "Pilih kriteria:",
            df_clean.columns,
            default=default_kriteria
        )

        mapping_kriteria = {f"C{i+1}": kriteria[i] for i in range(len(kriteria))}

        # =========================
        # 3️⃣ PILIH ALTERNATIF
        # =========================
        st.subheader("3️⃣ Pilih Alternatif")

        st.markdown("""
**Penjelasan:**
Alternatif adalah objek yang akan dibandingkan.

**Contoh:**
Varietas benih padi: A1, A2, A3, dll.
""")

        opsi_alternatif = [col for col in df_clean.columns if col not in kriteria]

        if not opsi_alternatif:
            st.warning("⚠️ Tidak ada kolom tersisa untuk alternatif!")
            alternatif = None
        else:
            default_alt = st.session_state.get("alternatif", None)

            index_alt = 0
            if default_alt in opsi_alternatif:
                index_alt = opsi_alternatif.index(default_alt)

            alternatif = st.selectbox(
                "Pilih alternatif:",
                opsi_alternatif,
                index=index_alt
            )

        # =========================
        # 4️⃣ SUB KRITERIA
        # =========================
        if kriteria:

            st.subheader("4️⃣ Penentuan Sub Kriteria")

            st.markdown("""
**Penjelasan:**
Sub kriteria digunakan untuk mengubah nilai asli menjadi skor numerik.

**Tujuan:**
Standarisasi nilai agar bisa dihitung oleh metode AHP & TOPSIS.
""")

            sub_config = {}

            old_sub_config = st.session_state.get("sub_config", {})

            for idx, k in enumerate(kriteria):

                st.markdown(f"### C{idx+1} - {k}")

                old_sub = old_sub_config.get(k, {})

                tipe_options = ["Numerik (Rentang)", "Kategorikal"]
                tipe_default = old_sub.get("tipe", "Numerik (Rentang)")

                tipe_index = tipe_options.index(tipe_default) if tipe_default in tipe_options else 0

                tipe = st.selectbox(
                    f"Tipe Data {k}",
                    tipe_options,
                    index=tipe_index,
                    key=f"tipe_{k}"
                )

                opsi_list = []

                old_opsi = old_sub.get("opsi", [])

                jumlah = st.number_input(
                    f"Jumlah Sub Kriteria {k}",
                    min_value=1,
                    max_value=10,
                    value=len(old_opsi) if old_opsi else 3,
                    step=1,
                    key=f"jumlah_{k}"
                )

                for i in range(int(jumlah)):

                    st.markdown(f"**Sub Kriteria {i+1}**")

                    cols = st.columns(3 if tipe=="Numerik (Rentang)" else 2)

                    if tipe == "Numerik (Rentang)":

                        old_o = old_opsi[i] if i < len(old_opsi) else {}

                        range_min = cols[0].number_input(
                            "Range Minimal",
                            step=0.1,
                            value=float(old_o.get("min", 0.0)),
                            key=f"{k}_min_{i}"
                        )

                        range_max = cols[1].number_input(
                            "Range Maksimal",
                            step=0.1,
                            value=float(old_o.get("max", 0.0)),
                            key=f"{k}_max_{i}"
                        )

                        nilai = cols[2].number_input(
                            "Nilai",
                            step=1,
                            value=int(old_o.get("nilai", 0)),
                            key=f"{k}_nilai_{i}"
                        )

                        opsi_list.append({"min":range_min,"max":range_max,"nilai":nilai})

                    else:

                        old_o = old_opsi[i] if i < len(old_opsi) else {}

                        kategori = cols[0].text_input(
                            "Kategori",
                            value=old_o.get("kategori", ""),
                            key=f"{k}_kat_{i}"
                        )

                        nilai = cols[1].number_input(
                            "Nilai",
                            step=1,
                            value=int(old_o.get("nilai", 0)),
                            key=f"{k}_nilai_kat_{i}"
                        )

                        opsi_list.append({"kategori":kategori,"nilai":nilai})

                    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

                sub_config[k] = {"tipe":tipe,"opsi":opsi_list}

        # =========================
        # SIMPAN PREPROCESSING
        # =========================
        if st.button("💾 Simpan Preprocessing"):

            try:
                if not kriteria:
                    st.error("❌ Kriteria belum dipilih!")
                    st.stop()

                if alternatif is None:
                    st.error("❌ Alternatif belum dipilih!")
                    st.stop()

                if not sub_config:
                    st.error("❌ Sub kriteria belum diisi!")
                    st.stop()

                df_final = pd.DataFrame()
                df_final["Alternatif"] = df_clean[alternatif]

                for k in kriteria:

                    hasil = []

                    for val in df_clean[k].astype(str):

                        skor = 0

                        if sub_config[k]["tipe"] == "Numerik (Rentang)":
                            for o in sub_config[k]["opsi"]:
                                try:
                                    val_float = float(str(val).replace(",", "."))
                                except:
                                    val_float = 0

                                if o["min"] <= val_float <= o["max"]:
                                    skor = o["nilai"]

                        else:
                            for o in sub_config[k]["opsi"]:
                                if str(val).lower() == str(o["kategori"]).lower():
                                    skor = o["nilai"]

                        hasil.append(skor)

                    kode = f"C{list(kriteria).index(k)+1}"
                    df_final[kode] = hasil

                if df_final.empty:
                    st.error("❌ Hasil preprocessing kosong!")
                    st.stop()

                # =========================
                # SIMPAN KE DATABASE
                # =========================
                save_db("preprocess", df_final.to_dict())

                save_db("config", {
                    "drop_cols": drop_cols,
                    "kriteria": kriteria,
                    "alternatif": alternatif,
                    "sub_config": sub_config,
                    "mapping_kriteria": mapping_kriteria
                })

                # =========================
                # SESSION
                # =========================
                st.session_state.data_preprocessed = df_final

                st.success("✅ Preprocessing berhasil disimpan! Mengalihkan ke Pembobotan...")

                time.sleep(3)

                st.session_state.menu = "Pembobotan"
                st.rerun()

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {e}")
# =========================
# PEMBOBOTAN (AHP)
# =========================
elif selected == "Pembobotan":

    st.title("Pembobotan Kriteria (AHP)")

    df = st.session_state.get("data_preprocessed")

    if df is None:
        st.warning("Lakukan preprocessing dulu")
    else:

        # =========================
        # Kriteria
        # =========================
        kriteria = [col for col in df.columns if col != "Alternatif"]
        kriteria = sorted(kriteria, key=lambda x: int(x.replace("C","")))
        n = len(kriteria)
        # =========================
        # LOAD DARI DB (BIAR GA RESET)
        # =========================
        config_db = load_db("config") or {}
        bobot_db = load_db("bobot") or {}

        if "ahp_matrix" in config_db and "ahp_matrix" not in st.session_state:
            st.session_state.ahp_matrix = pd.DataFrame(config_db["ahp_matrix"])
            st.session_state.ahp_matrix = st.session_state.ahp_matrix.reindex(index=kriteria, columns=kriteria)

        if "ahp" in bobot_db:
            st.session_state.bobot_ahp = pd.Series(bobot_db["ahp"])


        mapping = st.session_state.get("mapping_kriteria", {})

        # =========================
        # Mapping
        # =========================
        st.subheader("Mapping Kriteria")

        if mapping:
            mapping = {k: mapping.get(k, k) for k in kriteria}
            st.dataframe(pd.DataFrame({
                "Kode": list(mapping.keys()),
                "Nama Asli": list(mapping.values())
            }))

        st.info("Gunakan kode C1, C2, dst untuk perhitungan")

        # =========================
        # SKALA SAATY
        # =========================
        st.subheader("📊 Skala Saaty (AHP)")

        st.markdown("""
**Penjelasan:**
Skala Saaty digunakan untuk menentukan tingkat kepentingan antar kriteria.

**Tujuan:**
Membandingkan kriteria secara berpasangan.

**Contoh:**
- 1 → Sama penting  
- 3 → Sedikit lebih penting  
- 5 → Lebih penting  
- 7 → Sangat penting  
- 9 → Mutlak penting  
""")

        df_saaty = pd.DataFrame({
            "Intensitas": ["1","3","5","7","9","2,4,6,8","Kebalikan"],
            "Definisi": [
                "Sama penting","Sedikit lebih penting","Lebih penting",
                "Sangat lebih penting","Mutlak lebih penting",
                "Nilai kompromi","Kebalikan"
            ],
            "Keterangan": [
                "Kedua kriteria memiliki tingkat kepentingan yang sama",
                "Satu kriteria sedikit lebih penting dibandingkan kriteria lainnya",
                "Satu kriteria lebih penting dibandingkan kriteria lainnya",
                "Satu kriteria jelas lebih mutlak penting",
                "Satu kriteria memiliki kepentingan mutlak",
                "Nilai kompromi di antara dua tingkat kepentingan",
                "Jika elemen i memiliki nilai terhadap j, maka j bernilai kebalikannya"
            ]
        })

        st.dataframe(df_saaty, use_container_width=True)

        # =========================
        # AHP
        # =========================
        st.header("🔷 AHP")

        # 1️⃣ MATRKS
        st.subheader("1️⃣ Matriks Perbandingan")
        st.latex(r"A = [a_{ij}]")

        st.markdown("""
    **Penjelasan:**
    Matriks ini adalah hasil akhir dari input pengguna yang telah diperbaiki secara otomatis.

    **Aturan AHP yang diterapkan:**
    - Diagonal (C1 vs C1) = 1 → karena membandingkan dirinya sendiri
    - Hanya bagian atas diagonal yang diinput oleh user
    - Bagian bawah diagonal dihitung otomatis sebagai kebalikan (reciprocal)

    **Rumus:**
    Jika:
    aᵢⱼ = x  
    maka:
    aⱼᵢ = 1 / x  

    **Contoh:**
    Jika:
    C1 dibanding C2 = 3  

    Maka:
    C2 dibanding C1 = 1/3 = 0.333
    """)
        if "ahp_matrix" not in st.session_state or st.session_state.ahp_matrix is None:
            st.session_state.ahp_matrix = pd.DataFrame(
                [[1.0]*n for _ in range(n)],
                columns=kriteria,
                index=kriteria
            )

        edited = st.data_editor(
            st.session_state.ahp_matrix,
            use_container_width=True,
            key="ahp_editor"
        )

        # 🔥 FIX: pastikan DataFrame
        if isinstance(edited, dict):
            edited = pd.DataFrame(edited)

        edited = edited.astype(float)

        matrix = edited.copy()
        error_flag = False

        for i in range(n):
            for j in range(n):

                if i == j:
                    val = edited.iloc[i, j]

                    # ❌ jika user ubah diagonal
                    if not pd.isna(val) and val != 1:
                        st.error(f"❌ {kriteria[i]} dibanding {kriteria[j]} harus bernilai 1 (kriteria yang sama)")
                        error_flag = True

                    # 🔒 tetap paksa jadi 1
                    matrix.iloc[i, j] = 1.0

                elif i < j:
                    # ✔ hanya bagian atas boleh diisi
                    val = matrix.iloc[i, j]

                    if pd.isna(val) or val == 0 or val == "":
                        val = 1.0

                    try:
                        val = float(val)
                    except:
                        st.error(f"❌ Nilai tidak valid pada {kriteria[i]} vs {kriteria[j]}")
                        error_flag = True
                        continue

                    matrix.iloc[i, j] = val
                    matrix.iloc[j, i] = 1 / val

                elif i > j:
                    # 🔥 ambil nilai asli sebelum diedit
                    val_input = edited.iloc[i, j]
                    val_expected = matrix.iloc[i, j]  # hasil reciprocal

                    if not pd.isna(val_input) and abs(val_input - val_expected) > 1e-6:
                        st.error(f"❌ Jangan isi bagian bawah diagonal: {kriteria[i]} vs {kriteria[j]} isi hanya bagian atas saja! dan pastikan nilai diagonal bawah tetap None atau kosong")
                        error_flag = True

        # =========================
        # 🔥 TAMPILKAN MATRKS FINAL
        # =========================
        if not error_flag:
            st.session_state.ahp_matrix = matrix
            st.subheader("📊 Matriks Perbandingan Final (Otomatis)")
            st.dataframe(matrix, use_container_width=True)
            st.success("✅ Matriks sudah otomatis konsisten secara struktur (reciprocal)")
        else:
            st.warning("⚠️ Perbaiki input terlebih dahulu")

        # =========================
        # 2️⃣ JUMLAH KOLOM
        # =========================
        st.subheader("2️⃣ Jumlah Kolom")
        st.latex(r"\sum_{i=1}^{n} a_{ij}")

        st.markdown("""
**Penjelasan:**
Menjumlahkan nilai setiap kolom.

**Tujuan:**
Digunakan untuk normalisasi.

**Contoh:**
Kolom C1:
1 + 0.33 + 0.2 = 1.53
""")

        col_sum = matrix.sum(axis=0)
        st.dataframe(col_sum)

        # =========================
        # 3️⃣ NORMALISASI
        # =========================
        st.subheader("3️⃣ Normalisasi Matriks")
        st.latex(r"n_{ij} = \frac{a_{ij}}{\sum a_{ij}}")

        st.markdown("""
**Penjelasan:**
Setiap nilai dibagi jumlah kolomnya.

**Tujuan:**
Mengubah ke skala 0–1.

**Contoh:**
1 / 1.53 = 0.653
""")

        norm = matrix / col_sum
        st.dataframe(norm)

        # =========================
        # 4️⃣ BOBOT
        # =========================
        st.subheader("4️⃣ Bobot Kriteria")
        st.latex(r"w_i = \frac{1}{n} \sum n_{ij}")

        st.markdown("""
**Penjelasan:**
Rata-rata setiap baris.

**Tujuan:**
Menentukan prioritas kriteria.

**Contoh:**
(0.65 + 0.6 + 0.7)/3 = 0.65
""")

        bobot = norm.mean(axis=1)
        st.dataframe(bobot)

        # =========================
        # 5️⃣ WEIGHTED SUM
        # =========================
        st.subheader("5️⃣ Weighted Sum")
        st.latex(r"A \times w")

        st.markdown("""
**Penjelasan:**
Mengalikan matriks awal dengan bobot.

**Tujuan:**
Digunakan untuk uji konsistensi.

**Contoh:**
Aw = (1×0.65) + (3×0.2) + (5×0.15)
""")

        Aw = matrix.dot(bobot)
        st.dataframe(Aw)

        # =========================
        # 6️⃣ EIGEN VALUE
        # =========================
        st.subheader("6️⃣ Eigen Value")
        st.latex(r"\lambda_i = \frac{Aw}{w}")

        st.markdown("""
**Penjelasan:**
Membandingkan hasil weighted sum dengan bobot.

**Tujuan:**
Mengukur konsistensi tiap baris.

**Contoh:**
1.95 / 0.65 = 3
""")

        lambda_i = Aw / bobot
        st.dataframe(lambda_i)

        lambda_max = lambda_i.mean()
        st.write("λ max:", lambda_max)

        # =========================
        # 7️⃣ CI
        # =========================
        st.subheader("7️⃣ Consistency Index (CI)")
        st.latex(r"CI = \frac{\lambda_{max} - n}{n - 1}")

        st.markdown("""
**Penjelasan:**
Mengukur tingkat konsistensi.

**Contoh:**
(3.05 - 3) / 2 = 0.025
""")

        CI = (lambda_max - n) / (n - 1)
        st.write(CI)

        # =========================
        # 8️⃣ CR
        # =========================
        st.subheader("8️⃣ Consistency Ratio (CR)")
        st.latex(r"CR = \frac{CI}{RI}")

        st.markdown("""
**Penjelasan:**
Membandingkan CI dengan nilai random index.

**Interpretasi:**
- CR ≤ 0.1 → Konsisten  
- CR > 0.1 → Tidak Konsisten  
""")

        RI_dict = {3:0.52,4:0.89,5:1.11,6:1.25,7:1.35,8:1.40}
        CR = CI / RI_dict.get(n,1.49)

        st.write(CR)

        if CR <= 0.1:
            st.success("Konsisten")
        else:
            st.error("Tidak Konsisten")

        # =========================
        # 9️⃣ FINAL
        # =========================
        st.subheader("9️⃣ Bobot Final & Prioritas (AHP)")

        st.markdown("""
**Penjelasan:**
Bobot final adalah hasil akhir AHP.

**Interpretasi:**
Semakin besar → semakin penting.
""")

        df_ahp_final = pd.DataFrame({
            "Kriteria": bobot.index,
            "Bobot": bobot.values
        })

        df_ahp_final = df_ahp_final.sort_values(by="Bobot", ascending=False).reset_index(drop=True)
        df_ahp_final["Ranking"] = df_ahp_final.index + 1

        st.dataframe(df_ahp_final)

        st.success(f"Prioritas tertinggi: {df_ahp_final.iloc[0]['Kriteria']}")

        # =========================
        # FUZZY AHP
        # =========================
        st.header("🔶 Fuzzy AHP")

        # =========================
        # SKALA TFN
        # =========================
        st.subheader("📊 Skala TFN untuk Perbandingan Berpasangan")

        st.markdown("""
        **Penjelasan:**
        Skala TFN digunakan untuk mengubah nilai AHP menjadi bilangan fuzzy segitiga (Triangular Fuzzy Number).

        Setiap nilai memiliki 3 komponen:
        - l = lower (nilai bawah)
        - m = middle (nilai tengah)
        - u = upper (nilai atas)

        **Tujuan:**
        Mengatasi ketidakpastian dalam penilaian manusia.

        **Contoh:**
        Nilai 3 → (1, 1.5, 2)  
        Nilai 5 → (2, 2.5, 3)
        """)

        df_fuzzy = pd.DataFrame({
            "Skala AHP": [1,2,3,4,5,6,7,8,9],
            "TFN": [
                "(1,1,1)",
                "(1/2,1,3/2)",
                "(1,3/2,2)",
                "(3/2,2,5/2)",
                "(2,5/2,3)",
                "(5/2,3,7/2)",
                "(3,7/2,4)",
                "(7/2,4,9/2)",
                "(4,9/2,9/2)"
            ]
        })

        st.dataframe(df_fuzzy, use_container_width=True)

        # =========================
        # 1️⃣ KONVERSI
        # =========================
        st.subheader("1️⃣ Konversi Matriks AHP ke TFN")
        st.latex(r"\tilde{A} = (l,m,u)")

        st.markdown("""
        **Penjelasan:**
        Nilai matriks AHP dikonversi menjadi TFN.

        **Catatan Penting:**
        Karena hasil AHP bisa berupa desimal (misalnya 0.333),
        maka dilakukan pendekatan ke skala terdekat.

        **Contoh:**
        0.333 ≈ 1/3 → mendekati skala 3 → gunakan inverse TFN  
        3 → (1, 1.5, 2)
        """)

        def get_tfn_scale():
            return {
                1:(1,1,1),
                2:(0.5,1,1.5),
                3:(1,1.5,2),
                4:(1.5,2,2.5),
                5:(2,2.5,3),
                6:(2.5,3,3.5),
                7:(3,3.5,4),
                8:(3.5,4,4.5),
                9:(4,4.5,4.5)
            }

        def get_tfn_inverse(scale):
            l,m,u = scale
            return (1/u,1/m,1/l)

        def get_nearest_scale(x):
            skala = [1,2,3,4,5,6,7,8,9]
            if x >= 1:
                return min(skala, key=lambda s: abs(s - x))
            else:
                return min(skala, key=lambda s: abs(s - (1/x)))

        def to_tfn(x):
            if x == 0:
                return (0,0,0)

            scale = get_nearest_scale(x)

            if x >= 1:
                return get_tfn_scale()[scale]
            else:
                return get_tfn_inverse(get_tfn_scale()[scale])

        fuzzy = [[to_tfn(matrix.iloc[i,j]) for j in range(n)] for i in range(n)]

        df_fuzzy_full = pd.DataFrame(
            [[str(f) for f in row] for row in fuzzy],
            columns=kriteria,
            index=kriteria
        )

        st.write("Matriks TFN")
        st.dataframe(df_fuzzy_full)

        # =========================
        # 2️⃣ MATRKS L M U
        # =========================
        st.subheader("2️⃣ Matriks L, M, U")

        st.markdown("""
        **Penjelasan:**
        Matriks TFN dipisahkan menjadi 3 bagian:
        - L (Lower)
        - M (Middle)
        - U (Upper)

        **Tujuan:**
        Agar perhitungan fuzzy dilakukan per komponen.

        **Contoh:**
        (2,3,4) → L=2, M=3, U=4
        """)

        df_l = pd.DataFrame([[f[0] for f in r] for r in fuzzy], columns=kriteria, index=kriteria)
        df_m = pd.DataFrame([[f[1] for f in r] for r in fuzzy], columns=kriteria, index=kriteria)
        df_u = pd.DataFrame([[f[2] for f in r] for r in fuzzy], columns=kriteria, index=kriteria)

        st.write("Lower (L)")
        st.dataframe(df_l)

        st.write("Middle (M)")
        st.dataframe(df_m)

        st.write("Upper (U)")
        st.dataframe(df_u)

        # =========================
        # 3️⃣ GEOMETRIC MEAN
        # =========================
        st.subheader("3️⃣ Geometric Mean")
        st.latex(r"G_i = (\prod a_{ij})^{1/n}")

        st.markdown("""
        **Penjelasan:**
        Menghitung rata-rata geometrik tiap baris.

        **Tujuan:**
        Menggabungkan semua perbandingan menjadi satu nilai.

        **Contoh:**
        (1 × 3 × 5)^(1/3) = 2.466
        """)

        gm_l = df_l.prod(axis=1)**(1/n)
        gm_m = df_m.prod(axis=1)**(1/n)
        gm_u = df_u.prod(axis=1)**(1/n)

        df_gm = pd.DataFrame({
            "G_l": gm_l,
            "G_m": gm_m,
            "G_u": gm_u
        })

        st.dataframe(df_gm)

        # =========================
        # 4️⃣ NORMALISASI FUZZY
        # =========================
        st.subheader("4️⃣ Normalisasi Fuzzy")
        st.latex(r"w_i = \frac{G_i}{\sum G_i}")

        st.markdown("""
        **Penjelasan:**
        Membagi setiap nilai GM dengan totalnya.

        **Tujuan:**
        Mengubah menjadi bobot relatif.

        **Contoh:**
        0.25 / (0.25+0.30+0.20) = 0.33
        """)

        w_l = gm_l / gm_l.sum()
        w_m = gm_m / gm_m.sum()
        w_u = gm_u / gm_u.sum()

        df_w = pd.DataFrame({
            "w_l": w_l,
            "w_m": w_m,
            "w_u": w_u
        })

        st.dataframe(df_w)

        # =========================
        # 5️⃣ DEFUZZIFIKASI
        # =========================
        st.subheader("5️⃣ Defuzzifikasi")
        st.latex(r"W_i = \frac{w_l + w_m + w_u}{3}")

        st.markdown("""
        **Penjelasan:**
        Mengubah nilai fuzzy menjadi satu nilai tegas.

        **Tujuan:**
        Agar bisa digunakan dalam perhitungan TOPSIS.

        **Contoh:**
        (0.096 + 0.099 + 0.105)/3 = 0.100
        """)

        w_def = (w_l + w_m + w_u) / 3
        st.dataframe(w_def)

        # =========================
        # 6️⃣ NORMALISASI AKHIR
        # =========================
        st.subheader("6️⃣ Normalisasi Akhir")
        st.latex(r"w = \frac{W_i}{\sum W_i}")

        st.markdown("""
        **Penjelasan:**
        Menjadikan total bobot = 1.

        **Contoh:**
        0.2 / (0.2 + 0.3 + 0.5) = 0.2
        """)

        w_final = w_def / w_def.sum()
        st.dataframe(w_final)

        # =========================
        # 7️⃣ FINAL
        # =========================
        st.subheader("7️⃣ Bobot Final & Prioritas (Fuzzy AHP)")

        df_fuzzy_final = pd.DataFrame({
            "Kriteria": w_final.index,
            "Bobot": w_final.values
        })

        df_fuzzy_final = df_fuzzy_final.sort_values(by="Bobot", ascending=False).reset_index(drop=True)
        df_fuzzy_final["Ranking"] = df_fuzzy_final.index + 1

        st.dataframe(df_fuzzy_final)

        st.success(f"Prioritas tertinggi (Fuzzy): {df_fuzzy_final.iloc[0]['Kriteria']}")
        st.markdown("---")

        if st.button("💾 Simpan Bobot (AHP & Fuzzy)"):

            try:
                # =========================
                # VALIDASI
                # =========================
                if bobot is None or w_final is None:
                    st.error("❌ Bobot belum tersedia!")
                    st.stop()

                if matrix is None or matrix.empty:
                    st.error("❌ Matriks AHP kosong!")
                    st.stop()

                if bobot.sum() == 0 or w_final.sum() == 0:
                    st.error("❌ Bobot tidak valid (jumlah = 0)")
                    st.stop()

                # =========================
                # SIMPAN MATRIX (CONFIG)
                # =========================
                config_db = load_db("config") or {}

                config_db.update({
                    "ahp_matrix": matrix.to_dict()
                })

                save_db("config", config_db)

                # =========================
                # SIMPAN BOBOT
                # =========================
                save_db("bobot", {
                    "ahp": bobot.to_dict(),
                    "fuzzy": w_final.to_dict()
                })

                # =========================
                # SESSION
                # =========================
                st.session_state.bobot_ahp = bobot
                st.session_state.bobot_fuzzy = w_final

                # =========================
                # NOTIFIKASI
                # =========================
                st.success("✅ Bobot berhasil disimpan!")

                # ⏱️ DELAY
                time.sleep(3)

                # =========================
                # PINDAH HALAMAN
                # =========================
                st.session_state.menu = "Perangkingan"
                st.rerun()

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {e}")
# =========================
# PERANGKINGAN (TOPSIS - AHP)
# =========================
elif selected == "Perangkingan":

    st.title("Perangkingan Metode TOPSIS (AHP)")

    # =========================
    # LOAD DB (🔥 TAMBAHAN)
    # =========================
    df = st.session_state.get("data_preprocessed")

    bobot_db = load_db("bobot") or {}
    if "ahp" in bobot_db:
        st.session_state.bobot_ahp = pd.Series(bobot_db["ahp"])

    bobot = st.session_state.get("bobot_ahp")

    if df is None:
        st.warning("Data belum ada")
    elif bobot is None:
        st.warning("Bobot AHP & Fuzzy AHP belum tersedia")
    else:

        alternatif = df.iloc[:, 0]
        X = df.iloc[:, 1:]

        # =========================
        # 1️⃣ MATRKS KEPUTUSAN
        # =========================
        st.subheader("1️⃣ Matriks Keputusan")

        st.markdown("""
**Penjelasan:**
Matriks keputusan berisi nilai setiap alternatif terhadap setiap kriteria.

**Tujuan:**
Menjadi dasar perhitungan TOPSIS.

**Contoh:**
Jika A1 memiliki nilai 9 pada C1:
x11 = 9
""")

        df_X = pd.concat([alternatif, X], axis=1)
        st.dataframe(df_X)

        # =========================
        # 2️⃣ NORMALISASI
        # =========================
        st.subheader("2️⃣ Normalisasi Matriks")
        st.latex(r"r_{ij} = \frac{x_{ij}}{\sqrt{\sum x_{ij}^2}}")

        st.markdown("""
**Penjelasan:**
Normalisasi dilakukan untuk menyamakan skala antar kriteria.

**Tujuan:**
Agar semua kriteria dapat dibandingkan secara adil.

**Contoh:**
Nilai C1 = 9, 7, 9

√(9² + 7² + 9²) = √211 = 14.52

r11 = 9 / 14.52 = 0.62
""")

        pembagi = (X**2).sum()**0.5
        R = X / pembagi

        df_R = pd.concat([alternatif, R], axis=1)
        st.dataframe(df_R)

        # =========================
        # 3️⃣ TERBOBOT
        # =========================
        st.subheader("3️⃣ Matriks Ternormalisasi Terbobot")
        st.latex(r"y_{ij} = r_{ij} \times w_j")

        st.markdown("""
**Penjelasan:**
Mengalikan hasil normalisasi dengan bobot AHP.

**Tujuan:**
Menentukan kontribusi tiap kriteria.

**Contoh:**
r11 = 0.62  
w1 = 0.07  

y11 = 0.62 × 0.07 = 0.043
""")

        Y = R * bobot.values

        df_Y = pd.concat([alternatif, Y], axis=1)
        st.dataframe(df_Y)

        # =========================
        # 4️⃣ SOLUSI IDEAL
        # =========================
        st.subheader("4️⃣ Solusi Ideal Positif & Negatif")

        st.markdown("""
**Penjelasan:**
- A+ = nilai maksimum (terbaik)
- A- = nilai minimum (terburuk)

**Tujuan:**
Menentukan titik referensi terbaik dan terburuk.

**Contoh:**
0.02, 0.03, 0.01  

A+ = 0.03  
A- = 0.01
""")

        A_plus = Y.max()
        A_minus = Y.min()

        st.write("A+ (Positif)")
        st.dataframe(A_plus)

        st.write("A- (Negatif)")
        st.dataframe(A_minus)

        # =========================
        # 5️⃣ JARAK
        # =========================
        st.subheader("5️⃣ Jarak ke Solusi Ideal")

        st.latex(r"D_i^+ = \sqrt{\sum (y_{ij} - y_j^+)^2}")
        st.latex(r"D_i^- = \sqrt{\sum (y_{ij} - y_j^-)^2}")

        st.markdown("""
**Penjelasan:**
Mengukur jarak setiap alternatif terhadap solusi ideal.

**Tujuan:**
Menentukan seberapa dekat alternatif dengan kondisi terbaik.

**Contoh:**
(0.02 - 0.03)² = 0.0001
""")

        D_plus = ((Y - A_plus)**2).sum(axis=1)**0.5
        D_minus = ((Y - A_minus)**2).sum(axis=1)**0.5

        df_D = pd.DataFrame({
            "Alternatif": alternatif,
            "D+": D_plus,
            "D-": D_minus
        })

        st.dataframe(df_D)

        # =========================
        # 6️⃣ PREFERENSI
        # =========================
        st.subheader("6️⃣ Nilai Preferensi")
        st.latex(r"V_i = \frac{D_i^-}{D_i^+ + D_i^-}")

        st.markdown("""
**Penjelasan:**
Nilai preferensi menunjukkan kualitas alternatif.

**Interpretasi:**
Semakin mendekati 1 → semakin baik.

**Contoh:**
D+ = 0.1  
D- = 0.3  

V = 0.3 / (0.1 + 0.3) = 0.75
""")

        V = D_minus / (D_plus + D_minus)

        df_V = pd.DataFrame({
            "Alternatif": alternatif,
            "V": V
        })

        st.dataframe(df_V)

        # =========================
        # 7️⃣ RATA-RATA PREFERENSI + RANKING
        # =========================
        st.subheader("7️⃣ Rata-rata Preferensi & Ranking")

        st.markdown("""
**Penjelasan:**
Jika alternatif muncul lebih dari sekali, maka nilai preferensinya dirata-rata.

**Tujuan:**
Menghasilkan satu nilai final per alternatif.

**Contoh:**
A1 = 0.8 dan 0.9  

→ (0.8 + 0.9)/2 = 0.85
""")

        df_rank = df_V.groupby("Alternatif", as_index=False).agg({
            "V": "mean"
        })

        df_rank = df_rank.sort_values(by="V", ascending=False).reset_index(drop=True)
        df_rank["Ranking"] = df_rank.index + 1

        st.dataframe(df_rank)

        st.success(f"🏆 Alternatif terbaik: {df_rank.iloc[0]['Alternatif']}")

        # =========================
        # 🔥 SIMPAN KE DB
        # =========================
        save_db("ranking_ahp", df_rank.to_dict())
        
        # =========================
        # PERANGKINGAN (TOPSIS - FUZZY AHP)
        # =========================
        st.markdown("---")
        st.title("Perangkingan Metode TOPSIS (Fuzzy AHP)")

        # =========================
        # LOAD DB (🔥 TAMBAHAN)
        # =========================
        bobot_db = load_db("bobot") or {}
        if "fuzzy" in bobot_db:
            st.session_state.bobot_fuzzy = pd.Series(bobot_db["fuzzy"])

        bobot = st.session_state.get("bobot_fuzzy")

        if bobot is None:
            st.warning("Bobot Fuzzy belum tersedia")
        else:

            alternatif = df.iloc[:, 0]
            X = df.iloc[:, 1:]

            # =========================
            # 1️⃣ MATRKS KEPUTUSAN
            # =========================
            st.subheader("1️⃣ Matriks Keputusan (Fuzzy)")

            st.markdown("""
        **Penjelasan:**
        Matriks keputusan pada metode Fuzzy TOPSIS sama seperti AHP,
        namun bobot yang digunakan berasal dari hasil Fuzzy AHP.

        **Tujuan:**
        Menjadi dasar perhitungan TOPSIS berbasis fuzzy.

        **Contoh:**
        A1 pada C1 = 9
        """)

            df_X = pd.concat([alternatif, X], axis=1)
            st.dataframe(df_X)

            # =========================
            # 2️⃣ NORMALISASI
            # =========================
            st.subheader("2️⃣ Normalisasi Matriks")
            st.latex(r"r_{ij} = \frac{x_{ij}}{\sqrt{\sum x_{ij}^2}}")

            st.markdown("""
        **Penjelasan:**
        Normalisasi dilakukan untuk menyamakan skala antar kriteria.

        **Tujuan:**
        Agar semua kriteria memiliki kontribusi yang seimbang.

        **Contoh:**
        √(9² + 7² + 9²) = 14.52  
        r11 = 9 / 14.52 = 0.62
        """)

            pembagi = (X**2).sum()**0.5
            R = X / pembagi

            df_R = pd.concat([alternatif, R], axis=1)
            st.dataframe(df_R)

            # =========================
            # 3️⃣ TERBOBOT (FUZZY)
            # =========================
            st.subheader("3️⃣ Matriks Ternormalisasi Terbobot (Fuzzy)")
            st.latex(r"y_{ij} = r_{ij} \times w_j^{fuzzy}")

            st.markdown("""
        **Penjelasan:**
        Mengalikan hasil normalisasi dengan bobot dari Fuzzy AHP.

        **Tujuan:**
        Memasukkan ketidakpastian penilaian ke dalam perhitungan.

        **Contoh:**
        r11 = 0.62  
        w1 = 0.08  

        y11 = 0.62 × 0.08 = 0.0496
        """)

            Y = R * bobot.values

            df_Y = pd.concat([alternatif, Y], axis=1)
            st.dataframe(df_Y)

            # =========================
            # 4️⃣ SOLUSI IDEAL
            # =========================
            st.subheader("4️⃣ Solusi Ideal Positif & Negatif")

            st.markdown("""
        **Penjelasan:**
        - A+ = nilai maksimum (solusi terbaik)
        - A- = nilai minimum (solusi terburuk)

        **Tujuan:**
        Menentukan acuan pembanding untuk semua alternatif.

        **Contoh:**
        0.02, 0.03, 0.01  

        A+ = 0.03  
        A- = 0.01
        """)

            A_plus = Y.max()
            A_minus = Y.min()

            st.write("A+ (Positif)")
            st.dataframe(A_plus)

            st.write("A- (Negatif)")
            st.dataframe(A_minus)

            # =========================
            # 5️⃣ JARAK
            # =========================
            st.subheader("5️⃣ Jarak ke Solusi Ideal")

            st.latex(r"D_i^+ = \sqrt{\sum (y_{ij} - y_j^+)^2}")
            st.latex(r"D_i^- = \sqrt{\sum (y_{ij} - y_j^-)^2}")

            st.markdown("""
        **Penjelasan:**
        Menghitung jarak setiap alternatif terhadap solusi terbaik dan terburuk.

        **Tujuan:**
        Mengetahui seberapa dekat alternatif dengan kondisi ideal.

        **Contoh:**
        (0.02 - 0.03)² = 0.0001
        """)

            D_plus = ((Y - A_plus)**2).sum(axis=1)**0.5
            D_minus = ((Y - A_minus)**2).sum(axis=1)**0.5

            df_D = pd.DataFrame({
                "Alternatif": alternatif,
                "D+": D_plus,
                "D-": D_minus
            })

            st.dataframe(df_D)

            # =========================
            # 6️⃣ PREFERENSI
            # =========================
            st.subheader("6️⃣ Nilai Preferensi")
            st.latex(r"V_i = \frac{D_i^-}{D_i^+ + D_i^-}")

            st.markdown("""
        **Penjelasan:**
        Nilai preferensi menunjukkan tingkat kedekatan terhadap solusi ideal.

        **Interpretasi:**
        Semakin besar nilai V → semakin baik alternatif.

        **Contoh:**
        0.3 / (0.1 + 0.3) = 0.75
        """)

            V = D_minus / (D_plus + D_minus)

            df_V = pd.DataFrame({
                "Alternatif": alternatif,
                "V": V
            })

            st.dataframe(df_V)

            # =========================
            # 7️⃣ RATA-RATA + RANKING
            # =========================
            st.subheader("7️⃣ Rata-rata Preferensi & Ranking (Fuzzy)")

            st.markdown("""
        **Penjelasan:**
        Jika alternatif muncul lebih dari sekali, maka nilai preferensi dirata-rata.

        **Tujuan:**
        Menghasilkan satu nilai akhir per alternatif.

        **Contoh:**
        A1 = 0.8, 0.9  
        → (0.8 + 0.9) / 2 = 0.85
        """)

            df_rank = df_V.groupby("Alternatif", as_index=False).agg({
                "V": "mean"
            })

            df_rank = df_rank.sort_values(by="V", ascending=False).reset_index(drop=True)
            df_rank["Ranking"] = df_rank.index + 1

            st.dataframe(df_rank)

            st.success(f"🏆 Alternatif terbaik (Fuzzy): {df_rank.iloc[0]['Alternatif']}")

            # =========================
            # 🔥 SIMPAN KE DB
            # =========================
            save_db("ranking_fuzzy", df_rank.to_dict())

            # =========================
            # 🔥 SKENARIO (DINAMIS)
            # =========================
            st.markdown("---")
            st.header("🎯 Skenario Bobot & Perangkingan")

            st.markdown("""
            **Penjelasan:**
            Skenario digunakan untuk menguji sensitivitas perubahan bobot terhadap hasil perangkingan.

            **Tujuan:**
            Mengetahui apakah perubahan kecil pada bobot dapat mempengaruhi hasil akhir.

            **Cara kerja:**
            1. Pilih metode bobot (AHP / Fuzzy AHP)
            2. Ubah bobot (tukar / rotasi / manual)
            3. Sistem menghitung ulang TOPSIS
            4. Hasil dibandingkan dengan kondisi awal

            **Contoh:**
            Jika bobot awal:
            C1 = 0.4, C2 = 0.3  

            Ditukar:
            C1 = 0.3, C2 = 0.4  

            → hasil ranking bisa berubah
            """)

            # =========================
            # PILIH METODE
            # =========================
            metode_skenario = st.selectbox(
                "Pilih Bobot",
                ["AHP", "Fuzzy AHP"]
            )

            if metode_skenario == "AHP":
                bobot_awal = st.session_state.get("bobot_ahp")
            else:
                bobot_awal = st.session_state.get("bobot_fuzzy")

            if bobot_awal is None:
                st.warning("Bobot belum tersedia")
            else:

                # =========================
                # INPUT BOBOT
                # =========================
                st.subheader("🔧 Input / Edit Bobot Skenario")

                st.markdown("""
            **Penjelasan:**
            Bobot dapat diubah secara manual.

            **Tujuan:**
            Membuat berbagai variasi skenario.

            **Contoh:**
            - Tukar ranking ke-6 dan ke-7  
            - Rotasi bobot  
            - Ubah manual nilai bobot
            """)

                df_bobot = pd.DataFrame({
                    "Kriteria": bobot_awal.index,
                    "Bobot": bobot_awal.values
                }).sort_values(by="Bobot", ascending=False).reset_index(drop=True)

                df_bobot["Ranking"] = df_bobot.index + 1

                edited = st.data_editor(df_bobot, use_container_width=True)

                # =========================
                # AMBIL BOBOT
                # =========================
                bobot_skenario = pd.Series(
                    edited["Bobot"].values,
                    index=edited["Kriteria"]
                )

                bobot_skenario = bobot_skenario.reindex(X.columns)

                # =========================
                # HITUNG ULANG TOPSIS
                # =========================
                st.subheader("📊 Perhitungan TOPSIS Skenario")

                st.markdown("""
            **Penjelasan:**
            Menggunakan langkah TOPSIS yang sama, tetapi dengan bobot skenario.

            **Tahapan:**
            1. Normalisasi
            2. Pembobotan
            3. Solusi ideal
            4. Jarak
            5. Preferensi
            """)

                # 1 Normalisasi
                pembagi = (X**2).sum()**0.5
                R_s = X / pembagi

                # 2 Terbobot
                Y_s = R_s * bobot_skenario.values

                # 3 Solusi ideal
                A_plus_s = Y_s.max()
                A_minus_s = Y_s.min()

                # 4 Jarak
                D_plus_s = ((Y_s - A_plus_s)**2).sum(axis=1)**0.5
                D_minus_s = ((Y_s - A_minus_s)**2).sum(axis=1)**0.5

                # 5 Preferensi
                V_s = D_minus_s / (D_plus_s + D_minus_s)

                # =========================
                # HASIL
                # =========================
                st.subheader("📊 Hasil Ranking Skenario")

                df_skenario = pd.DataFrame({
                    "Alternatif": alternatif,
                    "Preferensi": V_s
                })

                df_skenario = df_skenario.groupby("Alternatif", as_index=False).mean()
                df_skenario = df_skenario.sort_values(by="Preferensi", ascending=False).reset_index(drop=True)
                df_skenario["Ranking"] = df_skenario.index + 1

                st.dataframe(df_skenario)

                st.success(f"🏆 Terbaik: {df_skenario.iloc[0]['Alternatif']}")

                # =========================
                # SIMPAN SKENARIO (DB)
                # =========================
                st.subheader("💾 Simpan Skenario")

                st.markdown("""
            **Penjelasan:**
            Skenario disimpan untuk evaluasi menggunakan:
            - Spearman Rank
            - NDCG

            Setiap skenario menyimpan:
            - Nama
            - Metode
            - Bobot
            - Ranking hasil
            """)

                # =========================
                # AUTO NAMA SKENARIO
                # =========================
                skenario_db = load_db("skenario") or []

                next_number = len(skenario_db) + 1
                default_nama = f"Skenario {next_number}"

                nama_skenario = st.text_input(
                    "Nama Skenario",
                    value=default_nama
                )
                # cek duplikat
                nama_list = [s["nama"] for s in skenario_db]

                if nama_skenario in nama_list:
                    st.error("❌ Nama skenario sudah ada!")
                    st.stop()

                if st.button("💾 Simpan Skenario"):

                    skenario_db = load_db("skenario") or []

                    skenario_db.append({
                        "nama": nama_skenario,
                        "metode": metode_skenario,
                        "bobot": bobot_skenario.to_dict(),
                        "ranking": df_skenario.to_dict()
                    })

                    save_db("skenario", skenario_db)

                    st.success(f"✅ {nama_skenario} berhasil disimpan!")

                # =========================
                # LIST SKENARIO
                # =========================
                st.subheader("📂 Daftar Skenario")

                skenario_db = load_db("skenario") or []

                if skenario_db:

                    for sk in skenario_db:

                        with st.expander(f"{sk['nama']} ({sk['metode']})"):

                            st.write("Bobot:")
                            st.dataframe(pd.DataFrame(sk["bobot"].items(), columns=["Kriteria","Bobot"]))

                            st.write("Ranking:")
                            st.dataframe(pd.DataFrame(sk["ranking"]))

                else:
                    st.info("Belum ada skenario")

                # =========================
                # 🗑️ HAPUS SEMUA SKENARIO
                # =========================
                st.markdown("---")
                st.subheader("🗑️ Hapus Semua Skenario")

                st.markdown("""
                **Penjelasan:**
                Fitur ini digunakan untuk menghapus seluruh skenario yang telah disimpan di database.

                **Catatan:**
                Aksi ini tidak dapat dibatalkan.
                """)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("🗑️ Hapus Semua Skenario"):

                        # konfirmasi manual sederhana
                        st.session_state.confirm_delete = True

                with col2:
                    if st.session_state.get("confirm_delete"):

                        if st.button("⚠️ Yakin Hapus Semua?"):

                            # 🔥 HAPUS DB
                            save_db("skenario", [])

                            # 🔥 RESET SESSION
                            st.session_state.confirm_delete = False

                            st.success("✅ Semua skenario berhasil dihapus!")

                            # refresh biar langsung kosong
                            st.rerun()

                # =========================
                # LANJUT
                # =========================
                st.markdown("---")

                if st.button("➡️ Lanjut ke Evaluasi"):
                    st.session_state.menu = "Evaluasi"
                    st.rerun()
# =========================
# EVALUASI (SEMUA SKENARIO)
# =========================
elif selected == "Evaluasi":

    st.title("Evaluasi Skenario (Spearman Rank Correlation & NDCG)")

    # =========================
    # LOAD SKENARIO (🔥 DB)
    # =========================
    skenario_list = load_db("skenario") or []

    if not skenario_list:
        st.warning("Belum ada skenario yang disimpan")
        st.stop()

    # =========================
    # INPUT RANK PAKAR
    # =========================
    st.subheader("1️⃣ Input Ranking Pakar")

    st.markdown("""
**Penjelasan:**
Ranking pakar merupakan urutan alternatif berdasarkan penilaian ahli.

**Tujuan:**
Digunakan sebagai pembanding terhadap hasil sistem.

**Aturan:**
- Tidak boleh ada ranking yang sama
- Harus berisi angka 1 sampai N
""")

    df = st.session_state.get("data_preprocessed")
    alternatif = df["Alternatif"].drop_duplicates().reset_index(drop=True)

    df_pakar = pd.DataFrame({
        "Alternatif": alternatif,
        "Rank Pakar": range(1, len(alternatif)+1)
    })

    df_pakar = st.data_editor(
        df_pakar,
        use_container_width=True,
        key="pakar_rank"
    )

    # =========================
    # VALIDASI
    # =========================
    if df_pakar["Rank Pakar"].duplicated().any():
        st.error("❌ Ranking tidak boleh ada yang sama!")
        st.stop()

    if set(df_pakar["Rank Pakar"]) != set(range(1, len(alternatif)+1)):
        st.error("❌ Ranking harus berisi angka 1 sampai N tanpa ada yang hilang!")
        st.stop()

    st.success("✅ Ranking pakar valid")

    # simpan
    st.session_state.rank_pakar = df_pakar.copy()

    # =========================
    # INPUT TOP-K NDCG
    # =========================
    st.subheader("2️⃣ Pengaturan NDCG")

    k = st.number_input(
        "Hitung NDCG Top-K",
        min_value=1,
        max_value=len(alternatif),
        value=min(5, len(alternatif))
    )

    # =========================
    # DETAIL SKENARIO 1
    # =========================
    st.header("🔍 Detail Perhitungan (Skenario 1)")

    skenario1 = skenario_list[0]
    df_rank = pd.DataFrame(skenario1["ranking"])

    df_merge = df_rank.merge(df_pakar, on="Alternatif", how="inner")

    # =========================
    # TABEL PERBANDINGAN
    # =========================
    st.subheader("3️⃣ Tabel Perbandingan Ranking")

    df_detail = df_merge[["Alternatif", "Ranking", "Rank Pakar"]].copy()
    df_detail["d"] = df_detail["Ranking"] - df_detail["Rank Pakar"]
    df_detail["d^2"] = df_detail["d"]**2

    st.dataframe(df_detail)

    # =========================
    # SPEARMAN
    # =========================
    st.subheader("4️⃣ Spearman Rank Correlation")

    n = len(df_detail)
    sum_d2 = df_detail["d^2"].sum()

    rho = 1 - (6 * sum_d2) / (n * (n**2 - 1))

    st.write(f"ρ = {rho:.4f}")

    # =========================
    # NDCG
    # =========================
    st.subheader("5️⃣ Perhitungan NDCG")

    df_ndcg = df_merge.sort_values("Preferensi", ascending=False).head(k).reset_index(drop=True)

    df_ndcg["Posisi"] = df_ndcg.index + 1
    df_ndcg["Rel"] = 1 / df_ndcg["Rank Pakar"]
    df_ndcg["Log"] = np.log2(df_ndcg["Posisi"] + 1)
    df_ndcg["DCG_i"] = df_ndcg["Rel"] / df_ndcg["Log"]

    st.dataframe(df_ndcg[["Alternatif","Posisi","Rel","Log","DCG_i"]])

    dcg = df_ndcg["DCG_i"].sum()

    df_idcg = df_ndcg.sort_values("Rel", ascending=False).reset_index(drop=True)
    df_idcg["Posisi"] = df_idcg.index + 1
    df_idcg["Log"] = np.log2(df_idcg["Posisi"] + 1)
    df_idcg["IDCG_i"] = df_idcg["Rel"] / df_idcg["Log"]

    st.dataframe(df_idcg[["Alternatif","Rel","Posisi","Log","IDCG_i"]])

    idcg = df_idcg["IDCG_i"].sum()

    ndcg_val = dcg / idcg if idcg != 0 else 0

    st.write(f"NDCG@{k} = {ndcg_val:.4f}")

    # =========================
    # SEMUA SKENARIO
    # =========================
    st.header("📊 Hasil Evaluasi Semua Skenario")

    hasil = []

    for s in skenario_list:

        df_rank = pd.DataFrame(s["ranking"])
        df_merge = df_rank.merge(df_pakar, on="Alternatif", how="inner")

        rank_model = df_merge["Ranking"]
        rank_pakar = df_merge["Rank Pakar"]

        # Spearman
        sp = 1 - (6 * ((rank_model - rank_pakar)**2).sum()) / (
            len(rank_model)*(len(rank_model)**2 -1)
        )

        # NDCG TOP-K
        df_eval = df_merge.sort_values("Preferensi", ascending=False).head(k)

        df_eval["rel"] = 1 / df_eval["Rank Pakar"]

        dcg = (df_eval["rel"] / np.log2(np.arange(2, len(df_eval)+2))).sum()

        df_ideal = df_eval.sort_values("rel", ascending=False)

        idcg = (df_ideal["rel"] / np.log2(np.arange(2, len(df_ideal)+2))).sum()

        nd = dcg / idcg if idcg != 0 else 0

        hasil.append({
            "Skenario": s["nama"],
            "Metode": s["metode"],
            "Spearman": round(sp,4),
            f"NDCG@{k}": round(nd,4)
        })

    df_hasil = pd.DataFrame(hasil)
    st.dataframe(df_hasil, use_container_width=True)

    # =========================
    # TERBAIK
    # =========================
    st.subheader("🏆 Skenario Terbaik")

    terbaik = df_hasil.sort_values(by="Spearman", ascending=False).iloc[0]

    st.success(f"""
Skenario Terbaik: {terbaik['Skenario']}
Metode: {terbaik['Metode']}
Spearman: {terbaik['Spearman']}
""")

    # =========================
    # 🔥 METODE PALING STABIL
    # =========================
    st.subheader("📊 Analisis Stabilitas Metode")

    df_stabil = df_hasil.groupby("Metode").agg({
        "Spearman": ["mean", "std"],
        f"NDCG@{k}": ["mean", "std"]
    }).reset_index()

    df_stabil.columns = [
        "Metode",
        "Mean Spearman",
        "Std Spearman",
        f"Mean NDCG@{k}",
        f"Std NDCG@{k}"
    ]

    st.dataframe(df_stabil, use_container_width=True)

    # 🔥 METODE PALING STABIL = STD TERKECIL
    terbaik_stabil = df_stabil.sort_values(by="Std Spearman").iloc[0]

    st.success(f"""
📌 Metode Paling Stabil: {terbaik_stabil['Metode']}

Alasan:
- Variasi Spearman paling kecil (Std = {terbaik_stabil['Std Spearman']:.4f})
- Hasil ranking paling konsisten antar skenario
""")