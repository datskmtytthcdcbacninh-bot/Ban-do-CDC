import unicodedata
import pandas as pd
import streamlit as st
import urllib.parse

def clean_name(text):
    """Hàm làm sạch và chuẩn hóa tên xã để so khớp với file GeoJSON"""
    if not isinstance(text, str):
        return ""
    text = (
        text.replace("Trạm Y tế", "")
        .replace("trạm y tế", "")
        .replace("Xã", "")
        .replace("Phường", "")
        .replace("Thị trấn", "")
        .replace("Y tế", "")
        .strip()
    )
    # Xóa dấu tiếng Việt
    text = unicodedata.normalize("NFD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text.lower()

def get_color(val):
    """Hệ màu hiển thị tỷ lệ"""
    if val < 20: return "#F1948A"
    elif val < 40: return "#F9E79F"
    elif val < 60: return "#85C1E9"
    elif val < 80: return "#2E86C1"
    else: return "#28B463"

@st.cache_data(ttl=300) # Lưu cache 5 phút để tránh quá tải API
def load_google_sheet(sheet_id, sheet_name):
    """Hàm tải dữ liệu từ Google Sheets định dạng CSV"""
    # Mã hóa tên sheet (chuyển dấu cách và tiếng Việt thành định dạng URL hợp lệ)
    encoded_sheet_name = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
    return pd.read_csv(url)