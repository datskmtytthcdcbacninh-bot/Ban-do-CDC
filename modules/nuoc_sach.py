import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import json
import glob
import os
import pandas as pd
import math
import re
import threading
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from utils import clean_name, get_color, load_google_sheet
from streamlit_autorefresh import st_autorefresh

# --- Kéo hệ thống cảnh báo từ tab Y tế sang ---
from modules.ghi_nhan_loi import (
    get_active_incidents, 
    lay_danh_sach_nguoi_nhan, 
    send_zalo_background_list, 
    hien_popup_desktop_tuy_chinh, 
    show_alert_modal
)

def render_page():
    # --- KHỞI TẠO BỘ NHỚ LƯU SỐ GIÂY (Mặc định 30s) ---
    if "refresh_sec_nuoc" not in st.session_state:
        st.session_state.refresh_sec_nuoc = 30

    col1, col2, col3 = st.columns([3, 1.5, 1])
    with col1:
        st.header("💧 Bản Đồ Tỷ Lệ Cấp Nước Sạch Tỉnh Bắc Ninh")
    
    with col2:
        st.write("") 
        # TẠO Ô NHẬP SỐ TỰ DO THAY CHO DROPDOWN
        refresh_sec = st.number_input(
            "⏱️ Tự động làm mới (giây):", 
            min_value=0, 
            value=st.session_state.refresh_sec_nuoc, 
            step=10,
            help="Nhập số giây để bản đồ tự làm mới. Nhập số 0 để TẮT."
        )
        st.session_state.refresh_sec_nuoc = refresh_sec
    
    with col3:
        st.write("")
        st.write("") # Thêm dòng trống để căn chỉnh nút bấm ngang hàng với ô nhập số
        if st.button("🔄 Làm mới ngay", use_container_width=True, help="Lấy số liệu thủ công ngay lập tức"):
            st.cache_data.clear() 
            st.rerun()            

    # --- KÍCH HOẠT VÒNG LẶP THỜI GIAN ---
    if refresh_sec > 0:
        st_autorefresh(interval=refresh_sec * 1000, key="dat_auto_refresh_state_nuoc")

    # =========================================================
    # FIX LỖI CACHE: Ép hệ thống xóa bộ nhớ đệm mỗi lần chạy lại 
    # để đảm bảo luôn tải dữ liệu mới nhất từ Google Form
    # =========================================================
    st.cache_data.clear()

    sheet_id = "1sIeZpXnwwJgRftbPVBfkOLRxLck0OjshNCVGkMe3W-k"
    
    try:
        df_tyle = load_google_sheet(sheet_id, "Ty_le_nuoc_sach")
        df_donvi = load_google_sheet(sheet_id, "Danh_sach_don_vi_cap_nuoc_va_dinh_vi")
        
        tram_incidents, xa_incidents = get_active_incidents(sheet_id)

        # =========================================================
        # HỆ THỐNG KIỂM SOÁT BÁO ĐỘNG DÙNG CHUNG
        # =========================================================
        if 'prev_xa_count' not in st.session_state:
            st.session_state.prev_xa_count = len(xa_incidents)
        if 'prev_tram_count' not in st.session_state:
            st.session_state.prev_tram_count = len(tram_incidents)

        trigger_alarm = False
        new_info = None
        nguon_phat_hien = ""

        if len(xa_incidents) > st.session_state.prev_xa_count:
            trigger_alarm = True
            new_info = xa_incidents[-1] 
            nguon_phat_hien = "Trạm Y Tế Xã"
        elif len(tram_incidents) > st.session_state.prev_tram_count:
            trigger_alarm = True
            new_info = tram_incidents[-1]
            nguon_phat_hien = "Đơn Vị Cấp Nước"

        if trigger_alarm and new_info:
            dia_ban_moi = new_info.get('ten', 'Không rõ')
            loai_su_co_zalo = new_info.get('loai', 'Sự cố')
            mo_ta_zalo = new_info.get('mo_ta', 'Không có')
            thoi_gian_zalo = new_info.get('thoi_gian', 'Đang cập nhật')
            nguoi_bao = new_info.get('nguoi_bao', 'Không cung cấp')
            sdt_bao = new_info.get('sdt_bao', 'Không cung cấp')
            link_zalo = new_info.get('link_zalo', 'https://bandocdc.bacninh.gov.vn')

            ds_nhan = []
            try:
                df_contacts = load_google_sheet(sheet_id, "Danh sách nhận cảnh báo")
                ds_nhan = lay_danh_sach_nguoi_nhan(df_contacts, loai_su_co_zalo, nguon_phat_hien)
            except Exception as e: print(f"Lỗi đọc danh bạ: {e}")
            
            if not ds_nhan: ds_nhan = ["0982518107"] 
                
            html_audio = """<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg"></audio>"""
            st.markdown(html_audio, unsafe_allow_html=True)
            
            noi_dung_zalo = f"🚨 BÁO CÁO SỰ CỐ MỚI 🚨\n🏢 Nguồn báo: {nguon_phat_hien.upper()}\n📍 Đơn vị/Địa bàn: {dia_ban_moi}\n🔥 Phân loại: {loai_su_co_zalo}\n📝 Mô tả: {mo_ta_zalo}\n🕒 Thời gian: {thoi_gian_zalo}\n👤 Người báo: {nguoi_bao} ({sdt_bao})\n👉 Xem chi tiết tại: {link_zalo}"
            threading.Thread(target=send_zalo_background_list, args=(ds_nhan, noi_dung_zalo)).start()

            hien_popup_desktop_tuy_chinh(dia_ban_moi, loai_su_co_zalo, mo_ta_zalo, thoi_gian_zalo, nguoi_bao, sdt_bao, nguon_phat_hien)

            st.session_state.prev_xa_count = len(xa_incidents)
            st.session_state.prev_tram_count = len(tram_incidents)
            show_alert_modal(dia_ban_moi, loai_su_co_zalo, mo_ta_zalo, thoi_gian_zalo, ds_nhan, nguon_phat_hien)

        elif len(xa_incidents) < st.session_state.prev_xa_count:
            st.session_state.prev_xa_count = len(xa_incidents)
        elif len(tram_incidents) < st.session_state.prev_tram_count:
            st.session_state.prev_tram_count = len(tram_incidents)
        # =========================================================

        tong_su_co_tram = len(tram_incidents)
        if tong_su_co_tram > 0:
            st.error(f"🚨 HỆ THỐNG GHI NHẬN {tong_su_co_tram} SỰ CỐ ĐƠN VỊ CẤP NƯỚC ĐANG DIỄN RA!")
            for sc in tram_incidents:
                st.warning(f"🏭 **Trạm cấp nước ({sc['ten']})**: {sc['loai']}")
        else:
            st.success("👉 Tất cả các Trạm cấp nước đang hoạt động bình thường. Sử dụng Layer Control để xem ranh giới xã.")

        df_tyle.columns = df_tyle.columns.astype(str).str.strip()
        ten_xa_col = next((c for c in df_tyle.columns if "xã" in str(c).lower() or "tên" in str(c).lower()), "Tên xã")
        ty_le_col = next((c for c in df_tyle.columns if "tỷ" in str(c).lower() or "ty le" in str(c).lower()), "Tỷ lệ")
        
        if ten_xa_col in df_tyle.columns:
            df_tyle["clean_key"] = df_tyle[ten_xa_col].apply(clean_name)
        
        def safe_float(val):
            try: return float(str(val).replace("%", "").replace(",", ".").strip())
            except: return 0.0
                
        if ty_le_col in df_tyle.columns:
            df_tyle["Ty_Le_Float"] = df_tyle[ty_le_col].apply(safe_float)
            data_dict = dict(zip(df_tyle["clean_key"], df_tyle["Ty_Le_Float"]))
        else:
            data_dict = {}

        geojson_files = [f for f in glob.glob("data/*.geojson") if "24_bac_ninh" not in f and "song_ngoi" not in f]
        
        combined_features = []
        labels_data = []
        all_commune_shapes = []

        for file_path in geojson_files:
            ten_hien_thi = os.path.splitext(os.path.basename(file_path))[0]
            clean_file_name = clean_name(ten_hien_thi)
            
            ty_le = 0
            for key, val in data_dict.items():
                if key in clean_file_name or clean_file_name in key:
                    ty_le = val; break
                    
            with open(file_path, "r", encoding="utf-8") as f:
                try: geo_data = json.load(f)
                except: continue
                
            ty_le_so = float(ty_le)
            mau_sac = get_color(ty_le_so)
                
            for feature in geo_data.get("features", []):
                geom_type = feature.get("geometry", {}).get("type", "")
                if "Polygon" not in geom_type: continue
                
                feature.setdefault("properties", {})
                feature["properties"]["Ten_Xa"] = ten_hien_thi
                feature["properties"]["Ty_Le"] = round(ty_le_so, 1)
                feature["properties"]["Mau_Sac"] = mau_sac
                combined_features.append(feature)
                
                try:
                    geom = shape(feature["geometry"])
                    all_commune_shapes.append(geom)
                    
                    center_pt = geom.centroid
                    if not geom.contains(center_pt): center_pt = geom.representative_point()

                    labels_data.append({
                        "name": ten_hien_thi, "clean_name": clean_file_name,
                        "val": round(ty_le_so, 1), "lat": center_pt.y, "lon": center_pt.x,
                    })
                except: pass

        combined_geojson = {"type": "FeatureCollection", "features": combined_features}

        m = folium.Map(location=[21.15, 106.05], zoom_start=10, tiles=None, control_scale=True)
        
        css_radar = """
        <style>
        .radar-marker { width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; color: white; font-size: 16px; box-shadow: 0px 4px 6px rgba(0,0,0,0.3); }
        .radar-blue { background-color: #3498DB; animation: pulse-blue 1.5s infinite; } @keyframes pulse-blue { 0% {box-shadow: 0 0 0 0 rgba(52,152,219,0.7);} 70% {box-shadow: 0 0 0 15px rgba(52,152,219,0);} 100% {box-shadow: 0 0 0 0 rgba(52,152,219,0);} }
        .radar-purple { background-color: #9B59B6; animation: pulse-purple 1.5s infinite; } @keyframes pulse-purple { 0% {box-shadow: 0 0 0 0 rgba(155,89,182,0.7);} 70% {box-shadow: 0 0 0 15px rgba(155,89,182,0);} 100% {box-shadow: 0 0 0 0 rgba(155,89,182,0);} }
        .radar-orange { background-color: #E67E22; animation: pulse-orange 1.5s infinite; } @keyframes pulse-orange { 0% {box-shadow: 0 0 0 0 rgba(230,126,34,0.7);} 70% {box-shadow: 0 0 0 15px rgba(230,126,34,0);} 100% {box-shadow: 0 0 0 0 rgba(230,126,34,0);} }
        .radar-darkred { background-color: #C0392B; animation: pulse-darkred 1.5s infinite; } @keyframes pulse-darkred { 0% {box-shadow: 0 0 0 0 rgba(192,57,43,0.7);} 70% {box-shadow: 0 0 0 15px rgba(192,57,43,0);} 100% {box-shadow: 0 0 0 0 rgba(192,57,43,0);} }
        .radar-red { background-color: #E74C3C; animation: pulse-red 1.5s infinite; } @keyframes pulse-red { 0% {box-shadow: 0 0 0 0 rgba(231,76,60,0.7);} 70% {box-shadow: 0 0 0 15px rgba(231,76,60,0);} 100% {box-shadow: 0 0 0 0 rgba(231,76,60,0);} }
        </style>
        """
        m.get_root().html.add_child(folium.Element(css_radar))

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Bản đồ nền', control=False
        ).add_to(m)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='🏷️ Tên Tỉnh Lân Cận', control=True, overlay=True
        ).add_to(m)
        
        song_ngoi_layer = folium.FeatureGroup(name="🌊 Sông chính", overlay=True, control=True)
        try:
            with open("data/song_ngoi.geojson", "r", encoding="utf-8") as f:
                song_geojson_data = json.load(f)

            province_boundary = unary_union(all_commune_shapes)

            filtered_features = []
            for feature in song_geojson_data.get("features", []):
                props = feature.get("properties", {})
                name = str(props.get("name", "")).strip()
                waterway = str(props.get("waterway", ""))
                natural = str(props.get("natural", ""))
                
                is_lake = (natural == "water") or ("Hồ" in name)
                is_small_drain = ("Ngòi" in name) or ("Mương" in name) or ("Kênh" in name) or ("Suối" in name) or ("drain" in waterway) or ("ditch" in waterway) or ("stream" in waterway)
                
                if not is_lake and not is_small_drain and name and name != "nan":
                    try:
                        river_geom = shape(feature["geometry"])
                        clipped_geom = river_geom.intersection(province_boundary)
                        if not clipped_geom.is_empty and clipped_geom.length > 0.04:
                            feature["geometry"] = mapping(clipped_geom)
                            filtered_features.append(feature)
                    except: pass
            song_geojson_data["features"] = filtered_features

            folium.GeoJson(
                song_geojson_data,
                style_function=lambda feature: {"color": "#0044FF", "weight": 3.5, "opacity": 1.0},
                tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Tên sông:"])
            ).add_to(song_ngoi_layer)
            song_ngoi_layer.add_to(m)
            
            river_labels_layer = folium.FeatureGroup(name="🏷️ Tên Sông", overlay=True, control=True)
            river_centroids = {}
            for feature in filtered_features:
                props = feature.get("properties", {})
                river_name = str(props.get("name", "")).strip()
                if river_name and river_name != "nan":
                    try:
                        geom = shape(feature["geometry"])
                        center_pt = geom.centroid
                        if river_name not in river_centroids: river_centroids[river_name] = []
                        river_centroids[river_name].append((center_pt.y, center_pt.x))
                    except: pass

            for river_name, pts in river_centroids.items():
                selected_pts = [pts[0]] if len(pts) == 1 else [pts[0], pts[len(pts) // 2]]
                for pt in selected_pts:
                    html_content = f'<div style="font-size:10px; font-weight:900; color:#0022AA; text-align:center; text-shadow: 2px 2px 3px white, -2px -2px 3px white, 2px -2px 3px white, -2px -2px 3px white, 0px 0px 5px white; pointer-events: none; width: 120px; transform: translate(-50%, -50%);">{river_name}</div>'
                    folium.map.Marker([pt[0], pt[1]], icon=DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=html_content)).add_to(river_labels_layer)
            river_labels_layer.add_to(m)
        except Exception: pass

        polygon_layer = folium.FeatureGroup(name="Màu sắc và viền các xã", overlay=True, control=False)
        folium.GeoJson(
            combined_geojson,
            style_function=lambda x: {"fillColor": x["properties"].get("Mau_Sac", "#cccccc"), "color": "#444444", "weight": 1, "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=["Ten_Xa", "Ty_Le"], aliases=["Xã/Phường:", "Tỷ lệ nước sạch (%):"])
        ).add_to(polygon_layer)
        polygon_layer.add_to(m)

        def add_label_filter_layer(min_val, max_val, layer_name, text_color):
            filtered_labels = [l for l in labels_data if min_val <= l["val"] < max_val]
            if not filtered_labels: return
            fg = folium.FeatureGroup(name=layer_name, overlay=True, control=True)
            for c in filtered_labels:
                html_content = f'<div style="font-size:9px; font-weight:bold; color:#000000; text-align:center; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white; pointer-events: none; width: 120px; transform: translate(-50%, -50%);">{c["name"]}<br><span style="color:{text_color}; font-size:10px;">{c["val"]}%</span></div>'
                folium.map.Marker([c["lat"], c["lon"]], icon=DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=html_content)).add_to(fg)
            fg.add_to(m)

        add_label_filter_layer(0, 20, "🏷️ Xã: < 20%", "#C0392B")
        add_label_filter_layer(20, 40, "🏷️ Xã: 20-40%", "#D4AC0D")
        add_label_filter_layer(40, 60, "🏷️ Xã: 40-60%", "#2980B9")
        add_label_filter_layer(60, 80, "🏷️ Xã: 60-80%", "#1B4F72")
        add_label_filter_layer(80, 101, "🏷️ Xã: > 80%", "#1E8449")

        tram_nuoc_layer = folium.FeatureGroup(name="🏭 Trạm Nước", overlay=True, control=True)
        canh_bao_layer = folium.FeatureGroup(name="🚨 Cảnh Báo Sự Cố", overlay=True, control=True)
        
        # 2. VẼ TRẠM CẤP NƯỚC (CHỈ RADAR TRẠM)
        if not df_donvi.empty:
            vi_do_idx, kinh_do_idx, ten_tram_idx, cong_suat_idx = None, None, None, None
            for i, col_name in enumerate(df_donvi.columns):
                c_str = str(col_name).lower()
                if "vĩ độ" in c_str: vi_do_idx = i
                elif "kinh độ" in c_str: kinh_do_idx = i
                elif "cấp nước" in c_str: ten_tram_idx = i 
                elif "m3" in c_str or "công suất" in c_str: cong_suat_idx = i
                
            for row_idx in range(min(5, len(df_donvi))):
                for col_idx in range(len(df_donvi.columns)):
                    cell_val = str(df_donvi.iloc[row_idx, col_idx]).lower()
                    if vi_do_idx is None and "vĩ độ" in cell_val: vi_do_idx = col_idx
                    if kinh_do_idx is None and "kinh độ" in cell_val: kinh_do_idx = col_idx
                    if ten_tram_idx is None and "cấp nước" in cell_val: ten_tram_idx = col_idx
                    if cong_suat_idx is None and ("m3" in cell_val or "công suất" in cell_val): cong_suat_idx = col_idx

            if ten_tram_idx is None and len(df_donvi.columns) > 1: ten_tram_idx = 1

            if vi_do_idx is not None and kinh_do_idx is not None:
                for row_idx in range(len(df_donvi)):
                    try:
                        lat_str = str(df_donvi.iloc[row_idx, vi_do_idx]).strip()
                        lon_str = str(df_donvi.iloc[row_idx, kinh_do_idx]).strip()
                        if lat_str.lower() in ['nan', '', 'none'] or lon_str.lower() in ['nan', '', 'none']: continue
                        lat, lon = float(lat_str), float(lon_str)
                        if not (8 < lat < 24) or not (102 < lon < 110): continue
                    except: continue
                        
                    ten_tram = str(df_donvi.iloc[row_idx, ten_tram_idx]) if ten_tram_idx is not None else "Trạm chưa rõ tên"
                    ten_tram = ten_tram.replace('\n', ' ').strip()
                    if ten_tram.lower() == "nan" or ten_tram == "": ten_tram = "Trạm chưa rõ tên"
                        
                    cong_suat = str(df_donvi.iloc[row_idx, cong_suat_idx]) if cong_suat_idx is not None else "0"
                    
                    try:
                        match = re.search(r'\d+([.,]\d+)*', cong_suat)
                        cs_num = float(match.group(0).replace(",", "").replace(".", "")) if match else 0
                    except: cs_num = 0

                    if cs_num < 1000:
                        ban_kinh, mau_vien, mau_nen = 3, "#145A32", "#27AE60"   
                    elif cs_num < 15000:
                        ban_kinh, mau_vien, mau_nen = 4, "#21618C", "#5DADE2"   
                    elif cs_num <= 30000:
                        ban_kinh, mau_vien, mau_nen = 5, "#935116", "#F39C12"   
                    else:
                        ban_kinh, mau_vien, mau_nen = 6, "#78281F", "#E74C3C"   
                    
                    popup_html_tram = f"<div style='min-width: 150px;'><b>{ten_tram}</b><br>Công suất: {cong_suat} m³/ngày đêm</div>"
                    
                    folium.CircleMarker(
                        location=[lat, lon], radius=ban_kinh, popup=folium.Popup(popup_html_tram, max_width=250),
                        tooltip=f"{ten_tram} (CS: {cong_suat})", color=mau_vien, weight=1.5,           
                        fill=True, fill_color=mau_nen, fill_opacity=0.9      
                    ).add_to(tram_nuoc_layer)

                    if tram_incidents:
                        for sc in tram_incidents:
                            if clean_name(sc['ten']) in clean_name(ten_tram) or clean_name(ten_tram) in clean_name(sc['ten']):
                                loai_su_co = sc.get('loai', 'Sự cố')
                                su_co_lower = loai_su_co.lower()
                                
                                if "vỡ" in su_co_lower or "hỏng" in su_co_lower or "rò" in su_co_lower or "bơm" in su_co_lower: color_class, fa_icon, hex_color = "orange", "wrench", "#E67E22"
                                elif "chất lượng" in su_co_lower or "đục" in su_co_lower or "mùi" in su_co_lower or "ô nhiễm" in su_co_lower: color_class, fa_icon, hex_color = "purple", "filter", "#9B59B6"
                                elif "áp lực" in su_co_lower or "yếu" in su_co_lower: color_class, fa_icon, hex_color = "blue", "tachometer", "#3498DB"
                                elif "mất nước" in su_co_lower or "ngừng" in su_co_lower or "cắt" in su_co_lower: color_class, fa_icon, hex_color = "red", "tint", "#E74C3C"
                                else: color_class, fa_icon, hex_color = "red", "exclamation-triangle", "#C0392B"

                                icon_html = f'<div class="radar-marker radar-{color_class}"><i class="fa fa-{fa_icon}"></i></div>'
                                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
                                
                                popup_html_sc_tram = f"""
                                <div style="width: 280px; font-family: Arial, sans-serif;">
                                    <h4 style="color: {hex_color}; margin-top:0; border-bottom: 2px solid {hex_color}; padding-bottom: 5px; text-transform: uppercase;"><i class="fa fa-{fa_icon}"></i> CẢNH BÁO TRẠM NƯỚC</h4>
                                    <b>📍 Đơn vị:</b> {ten_tram}<br>
                                    <b>🔥 Lỗi:</b> {loai_su_co}<br>
                                    <b>🕒 Thời gian:</b> {sc.get('thoi_gian', 'Đang cập nhật')}<br>
                                    <b>👤 Người báo:</b> <span style="color:#2980B9; font-weight:bold;">{sc.get('nguoi_bao', 'Không rõ')}</span> - 📞 {sc.get('sdt_bao', 'Không rõ')}<br>
                                    <b>🛠️ Xử lý:</b> {sc.get('xu_ly', 'Đang xử lý')}<br><br>
                                    <a href="{maps_url}" target="_blank" style="background-color: {hex_color}; color: white; padding: 8px 10px; text-decoration: none; border-radius: 4px; display: inline-block; text-align: center; width: 100%; font-weight:bold; box-shadow: 0px 2px 4px rgba(0,0,0,0.3); transition: 0.3s;">🗺️ Dẫn đường tới trạm</a>
                                </div>
                                """
                                tooltip_text = folium.Tooltip(f"<b>{ten_tram}</b><br><i style='color:red;'>👉 Bấm để xem chi tiết sự cố</i>")

                                folium.map.Marker(
                                    [lat, lon],
                                    icon=DivIcon(icon_size=(35, 35), icon_anchor=(17, 17), html=icon_html),
                                    popup=folium.Popup(popup_html_sc_tram, max_width=320),
                                    tooltip=tooltip_text
                                ).add_to(canh_bao_layer)
                                break

        tram_nuoc_layer.add_to(m)
        canh_bao_layer.add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)

        legend_html = """
        <style>
        .leaflet-right .leaflet-control { margin-right: 15px !important; }
        .leaflet-top .leaflet-control { margin-top: 15px !important; }
        .leaflet-control-layers-expanded { padding: 6px 10px !important; font-size: 11px !important; width: max-content !important; min-width: 130px !important; max-width: 160px !important; overflow: hidden !important; }
        .leaflet-control-layers-list label { display: flex !important; align-items: center !important; margin-bottom: 3px !important; line-height: 1.2 !important; white-space: nowrap !important; }
        .leaflet-control-layers-selector { margin-top: 0px !important; margin-right: 6px !important; }
        .leaflet-control-attribution { display: none !important; }
        </style>
        
        <div style="position: absolute; bottom: 15px; right: 15px; width: 125px; height: auto; background-color: rgba(255, 255, 255, 0.95); border: 1px solid grey; z-index: 9999; font-size: 11px; padding: 6px; border-radius: 4px; box-shadow: 1px 1px 4px rgba(0,0,0,0.3); pointer-events: none; line-height: 1.3;">
            <b style="font-size: 11px; display:block; margin-bottom:5px; text-align: center;">Màu Tỷ lệ (%)</b>
            <div style="margin-bottom:3px;"><i style="background:#F1948A; width:9px; height:9px; display:inline-block; margin-right:5px; border-radius:1px;"></i>< 20 (Đỏ)</div>
            <div style="margin-bottom:3px;"><i style="background:#F9E79F; width:9px; height:9px; display:inline-block; margin-right:5px; border-radius:1px;"></i>20-40 (Vàng)</div>
            <div style="margin-bottom:3px;"><i style="background:#85C1E9; width:9px; height:9px; display:inline-block; margin-right:5px; border-radius:1px;"></i>40-60 (Xanh)</div>
            <div style="margin-bottom:3px;"><i style="background:#2E86C1; width:9px; height:9px; display:inline-block; margin-right:5px; border-radius:1px;"></i>60-80 (Đậm)</div>
            <div><i style="background:#28B463; width:9px; height:9px; display:inline-block; margin-right:5px; border-radius:1px;"></i>> 80 (Lá)</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, use_container_width=True, height=700, returned_objects=[])
        
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu: {e}")