import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Trỏ đúng thư mục Zalo_Data
zalo_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Zalo_Data')

options = Options()
options.add_argument(f"user-data-dir={zalo_data_path}")
options.add_experimental_option("excludeSwitches", ["enable-automation"])

print("Đang mở trình duyệt Chrome...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://chat.zalo.me")

print("Vui lòng QUÉT MÃ QR trên trình duyệt vừa mở để đăng nhập Zalo.")
print("Sau khi Zalo tải xong danh bạ và tin nhắn, hãy đóng cửa sổ trình duyệt này.")

# Giữ trình duyệt mở để bác quét QR
while True:
    time.sleep(1)