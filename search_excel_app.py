import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
import os

# ================== CONFIG ==================
st.set_page_config(page_title="Tìm IP", layout="wide")

# ----------- BACKGROUND -----------
st.markdown("""
<style>
.stApp {
    background-image: url("https://images.unsplash.com/photo-1588526779453-57a0d3d15963?q=80&w=735&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
    background-size: cover;
    background-attachment: fixed;
}
section.main > div {
    background: rgba(255,255,255,0.75);
    border-radius: 16px;
    padding: 32px;
}
</style>
""", unsafe_allow_html=True)
#Test6
# ================== DATA DIR ==================
BASE_DATA_DIR = os.environ.get("DATA_DIR", "/opt/streamlit-data")

#UPLOAD_DIR = os.path.join(BASE_DATA_DIR, "uploads")
SAVE_DIR = os.path.join(BASE_DATA_DIR, "uploads")
#SAVE_DIR = os.path.join(BASE_DATA_DIR, "saved_files")

#os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAVE_DIR, exist_ok=True)
#SAVE_DIR = "uploads"
#os.makedirs(SAVE_DIR, exist_ok=True)

# ================== ACCOUNTS ==================
credentials = {
    "usernames": {
        "admin": {
            "name": "admin",
            "password": "$2b$12$J6uzJMsrTZ62l3gkfFyDquxdXxpNH3whzPxXocp3zVGLoueUCrqTm",
            "role": "admin"
        },
        "user": {
            "name": "user",
            "password": "$2b$12$h91600SujrEhw79gglaFdexYb8AUJUl7nagESixnH0T8yoHQ2mBk6",
            "role": "viewer"
        }
    }
}

# ================== AUTH ==================
authenticator = stauth.Authenticate(
    credentials,
    "excel_cookie",
    "abcdef",
    1,
    prehashed=True
)

authenticator.login("main")

if st.session_state.get("authentication_status") is None:
    st.warning("🔒 Vui lòng đăng nhập")
    st.stop()

if st.session_state.get("authentication_status") is False:
    st.error("❌ Sai tài khoản hoặc mật khẩu")
    st.stop()

username = next(
    u for u, i in credentials["usernames"].items()
    if i["name"] == st.session_state["name"]
)
role = credentials["usernames"][username]["role"]

st.sidebar.success(f"🧑‍💻 {username}")
st.sidebar.info(f"⚙️ Role: {role}")
authenticator.logout("⏻ Đăng xuất", "sidebar")

# ================== CACHE LOAD ALL FILES ==================
@st.cache_data(show_spinner="📂 Đang load & cache toàn bộ dữ liệu...")
def load_all_files():
    rows = []
    for fname in os.listdir(SAVE_DIR):
        if not fname.endswith((".csv", ".xlsx", ".xls")):
            continue
        path = os.path.join(SAVE_DIR, fname)
        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(path, dtype=str).fillna("")
                df["__file__"] = fname
                df["__sheet__"] = "CSV"
                rows.append(df)
            else:
                xls = pd.ExcelFile(path)
                for s in xls.sheet_names:
                    df = xls.parse(s, dtype=str).fillna("")
                    df["__file__"] = fname
                    df["__sheet__"] = s
                    rows.append(df)
        except:
            pass

    if not rows:
        return pd.DataFrame()

    df_all = pd.concat(rows, ignore_index=True)

    df_all["__search__"] = (
        df_all.astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )
    return df_all

df_all = load_all_files()

# ================== FILE LIST ==================
saved_files = sorted(
    f for f in os.listdir(SAVE_DIR)
    if f.endswith((".csv", ".xlsx", ".xls"))
)

# ================== SEARCH (CLEAN + FAST) ==================
st.header("🔎 Tìm kiếm")

query = st.text_input("Nhập từ khoá (IP / hostname / bất kỳ)")

if query:
    if df_all.empty:
        st.warning("Chưa có dữ liệu")
    else:
        q = query.lower().strip()

        res = df_all[df_all["__search__"].str.contains(q, na=False)]

        if not res.empty:
            # Bỏ cột search
            res = res.drop(columns=["__search__"])

            # Chuẩn hoá dữ liệu rỗng
            res = res.fillna("").replace("None", "")

            # Bỏ cột Unnamed
            res = res.loc[:, ~res.columns.str.contains("^Unnamed")]

            # Chỉ giữ cột có ít nhất 1 giá trị khác rỗng
            res = res.loc[:, (res != "").any(axis=0)]

            st.dataframe(res, use_container_width=True)
        else:
            st.warning("Không tìm thấy kết quả")
# ================== UPLOAD ==================
st.header("📁 Upload file")

uploads = st.file_uploader(
    "Chọn file CSV / Excel",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

if uploads:
    for f in uploads:
        with open(os.path.join(SAVE_DIR, f.name), "wb") as out:
            out.write(f.getbuffer())
    st.cache_data.clear()
    st.success("✅ Upload thành công")
    st.rerun()

# ================== DELETE FILE ==================
st.sidebar.header("🗑️ Quản lý file")

if saved_files:
    del_file = st.sidebar.selectbox("Chọn file", saved_files)
    if st.sidebar.button("❌ Xoá file"):
        if role != "admin":
            st.sidebar.error("⛔ Không có quyền")
        else:
            os.remove(os.path.join(SAVE_DIR, del_file))
            st.cache_data.clear()
            st.sidebar.success("✅ Đã xoá file")
            st.rerun()

# ================== VIEW FILE (CACHED) ==================
@st.cache_data
def load_single_file(path):
    if path.endswith(".csv"):
        return {"CSV": pd.read_csv(path)}
    xls = pd.ExcelFile(path)
    return {s: xls.parse(s) for s in xls.sheet_names}

st.header("📄 Xem file")

if saved_files:
    file_to_open = st.selectbox("Chọn file", saved_files)
    file_path = os.path.join(SAVE_DIR, file_to_open)

    file_data = load_single_file(file_path)
    sheet = st.selectbox("Sheet", file_data.keys())
    df = file_data[sheet]

    st.dataframe(df, use_container_width=True)
else:
    st.info("Chưa có file nào")

# ================== VIEWER STOP ==================
if role != "admin":
    st.info("👀 Viewer chỉ xem / tìm kiếm / upload")
    st.stop()

# ================== ADMIN EDIT ==================
st.header("✏️ Chỉnh sửa dữ liệu (Admin)")
# ================== ADD ROW ==================
with st.expander("➕ Thêm dòng mới"):
    new_data = {}
    for col in df.columns:
        new_data[col] = st.text_input(f"{col}", key=f"add_{col}")

    if st.button("➕ Thêm dòng"):
        new_row_df = pd.DataFrame([new_data])
        df_updated = pd.concat([df, new_row_df], ignore_index=True)

        if file_to_open.endswith(".csv"):
            df_updated.to_csv(file_path, index=False)
        else:
            with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
                df_updated.to_excel(w, sheet_name=sheet, index=False)

        st.cache_data.clear()
        st.success("✅ Đã thêm dòng")
        st.rerun()


# ================== ADD COLUMN ==================
with st.expander("➕ Thêm cột mới"):
    new_col_name = st.text_input("Tên cột mới")

    if st.button("➕ Thêm cột"):
        if new_col_name and new_col_name not in df.columns:
            df[new_col_name] = ""

            if file_to_open.endswith(".csv"):
                df.to_csv(file_path, index=False)
            else:
                with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
                    df.to_excel(w, sheet_name=sheet, index=False)

            st.cache_data.clear()
            st.success(f"✅ Đã thêm cột '{new_col_name}'")
            st.rerun()
        else:
            st.warning("Tên cột không hợp lệ hoặc đã tồn tại")
# ================== DELETE ROW ==================
with st.expander("🗑️ Xoá dòng"):
    if not df.empty:
        row_index = st.number_input(
            "Nhập index dòng cần xoá",
            min_value=0,
            max_value=len(df) - 1,
            step=1,
            key="delete_row_index"
        )

        if st.button("❌ Xoá dòng"):
            df_updated = df.drop(index=row_index).reset_index(drop=True)

            if file_to_open.endswith(".csv"):
                df_updated.to_csv(file_path, index=False)
            else:
                with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
                    df_updated.to_excel(w, sheet_name=sheet, index=False)

            st.cache_data.clear()
            st.success(f"✅ Đã xoá dòng {row_index}")
            st.rerun()
    else:
        st.info("File không có dữ liệu")


# ================== DELETE COLUMN ==================
with st.expander("🗑️ Xoá cột"):
    if not df.empty:
        col_to_delete = st.selectbox(
            "Chọn cột cần xoá",
            df.columns,
            key="delete_column_select"
        )

        if st.button("❌ Xoá cột"):
            df_updated = df.drop(columns=[col_to_delete])

            if file_to_open.endswith(".csv"):
                df_updated.to_csv(file_path, index=False)
            else:
                with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
                    df_updated.to_excel(w, sheet_name=sheet, index=False)

            st.cache_data.clear()
            st.success(f"✅ Đã xoá cột '{col_to_delete}'")
            st.rerun()
    else:
        st.info("File không có dữ liệu")            
edited = st.data_editor(df, use_container_width=True)

if st.button("💾 Lưu thay đổi"):
    if file_to_open.endswith(".csv"):
        edited.to_csv(file_path, index=False)
    else:
        with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
            edited.to_excel(w, sheet_name=sheet, index=False)

    st.cache_data.clear()
    st.success("✅ Đã lưu file")
    st.rerun()

