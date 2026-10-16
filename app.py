import streamlit as st
from modules import nuoc_sach, ghi_nhan_loi

# Cấu hình toàn trang
st.set_page_config(page_title="Hệ thống GIS - CDC Bắc Ninh", layout="wide", page_icon="📍")

# Sidebar - Menu điều hướng
st.sidebar.title("📌 DANH MỤC QUẢN LÝ")

menu = st.sidebar.radio(
    "Chọn Chuyên đề cần hiển thị:",
    ("💧 Quản lý Nước sạch", "🚨 Ghi nhận lỗi / Sự cố", "🏫 Y tế Trường học (Sắp ra mắt)")
)

st.sidebar.markdown("---")
st.sidebar.info("Hệ thống GIS quản lý Sức khỏe Môi trường & Y tế Trường học - CDC Bắc Ninh")

# Điều hướng hiển thị
if menu == "💧 Quản lý Nước sạch":
    nuoc_sach.render_page()
    
elif menu == "🚨 Ghi nhận lỗi / Sự cố":
    ghi_nhan_loi.render_page()
    
elif menu == "🏫 Y tế Trường học (Sắp ra mắt)":
    st.header("🏫 Y tế Trường học")
    st.info("Module quản lý vệ sinh và tai nạn thương tích trường học đang được phát triển.")