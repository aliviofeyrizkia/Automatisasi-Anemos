# =========================================
# ================= BMKG ==================
# (100% IDENTIK - TIDAK DIUBAH)
# =========================================

import time
import csv
import re
from datetime import datetime, timedelta

import pytesseract
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import os

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
TARGET = ["10:00","13:00","16:00","19:00","22:00"]
MAX_RETRY = 5   # maksimal ulang 5 kali


def ambil_data():

    hasil = {}

    service = Service()

    options = webdriver.ChromeOptions()

    options.binary_location = "/usr/bin/chromium-browser"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://www.bmkg.go.id/cuaca/prakiraan-cuaca/32.11.15.2005")

        besok_obj = datetime.now() + timedelta(days=1)
        besok_text = besok_obj.strftime("%d %b")

        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//button[contains(text(),'{besok_text}')]")
            )
        ).click()

        time.sleep(8)
        driver.execute_script("window.scrollTo(0, 900);")
        time.sleep(3)

        start_time = time.time()
        max_duration = 90
        slide = 0

        while time.time() - start_time < max_duration:

            slide += 1
            print(f"Slide {slide}")

            filename = f"slide_{slide}.png"
            driver.save_screenshot(filename)

            img = Image.open(filename).convert("L")
            img = img.resize((img.width*2, img.height*2))

            text = pytesseract.image_to_string(img)

            text = text.replace(";", ":").replace(".", ":")

            for jam in TARGET:

                if jam in hasil:
                    continue

                if jam in text:

                    pattern = rf"{jam}(.{{0,200}})"
                    match = re.search(pattern, text, re.DOTALL)

                    if match:
                        blok = match.group(0)

                        suhu = re.search(r"(\d+)\s?°", blok)
                        rh = re.search(r"(\d+)%", blok)
                        cuaca = re.search(
                            r"(Cerah|Berawan|Hujan Ringan|Hujan Sedang|Hujan Lebat)",
                            blok
                        )

                        if suhu and rh and cuaca:
                            hasil[jam] = [
                                suhu.group(1),
                                cuaca.group(1),
                                rh.group(1)
                            ]
                            print("✔", jam, hasil[jam])

            if len(hasil) == len(TARGET):
                print("SEMUA DATA LENGKAP")
                break

            try:
                next_btn = driver.find_element(By.CLASS_NAME, "swiper-button-next")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
            except:
                time.sleep(3)

    finally:
        driver.quit()

    return hasil


for attempt in range(1, MAX_RETRY+1):

    print(f"\n=== PERCOBAAN KE {attempt} ===")

    hasil = ambil_data()

    if len(hasil) == len(TARGET):
        print("DATA BERHASIL DIAMBIL 100%")
        break
    else:
        print("Data belum lengkap, ulang...\n")
        time.sleep(8)

else:
    print("Gagal setelah beberapa percobaan.")


if hasil:

    besok_obj = datetime.now() + timedelta(days=1)

    with open("bmkg_dago.csv","w",newline="",encoding="utf8") as f:
        writer = csv.writer(f)
        writer.writerow(["tanggal","jam","suhu_C","cuaca","RH_%"])

        for jam, data in hasil.items():
            writer.writerow([besok_obj.strftime("%d-%m-%Y"), jam, *data])

    print("\nCSV BERHASIL DISIMPAN → bmkg_dago.csv\n")

else:
    print("Tidak ada data untuk disimpan.")


# =========================================
# ============== METEOLOGIX ===============
# (100% IDENTIK - TIDAK DIUBAH)
# =========================================

import time
import csv
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL = "https://meteologix.com/id/forecast/1949683-sayang/xl/deu"

TARGET_JAM = [
"10:00am",
"01:00pm",
"04:00pm",
"07:00pm",
"10:00pm"
]

MODEL = {
    "ICON":"deu",
    "GFS":"usa",
    "ECMWF":"rapid-euro"
}


def klik_accept_cookie(driver):

    wait = WebDriverWait(driver,8)

    print("Mencari tombol Accept cookie...")

    try:
        btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,"//button[contains(.,'Accept')]")
            )
        )
        btn.click()
        print("Cookie accepted (direct)")
        return
    except:
        pass

    iframes = driver.find_elements(By.TAG_NAME,"iframe")

    for frame in iframes:

        try:
            driver.switch_to.frame(frame)

            btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,"//button[contains(.,'Accept')]")
                )
            )

            btn.click()
            print("Cookie accepted (iframe)")
            driver.switch_to.default_content()
            return

        except:
            driver.switch_to.default_content()

    driver.execute_script("""
        document.querySelectorAll('[role="dialog"]').forEach(e=>e.remove());
        document.body.style.overflow='auto';
    """)

    print("Popup cookie dihapus paksa")


def ambil_data_panel(text):

    lines = text.split("\n")

    temperature=""
    humidity=""
    rain=""
    wind=""

    for i,line in enumerate(lines):

        if line.strip()=="Temperature":
            temperature = lines[i+1]

        if line.strip()=="Humidity":
            humidity = lines[i+1]

        if line.strip()=="Precipitation":
            rain = lines[i+1]

        if line.strip()=="Wind":
            wind = lines[i+1]

    return temperature,humidity,rain,wind


options = Options()

options.binary_location = "/usr/bin/chromium-browser"

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver,20)

driver.get(URL)
time.sleep(8)

klik_accept_cookie(driver)
time.sleep(5)

driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(5)

driver.execute_script("window.scrollTo(0, 1200)")
time.sleep(5)

data_all = []

for model_name, model_value in MODEL.items():
    print("\nMODEL:", model_name)

    success = False

    for attempt in range(3):
        try:
            print(f"Percobaan {attempt+1} cari tombol...")

            # 🔥 scroll paksa load element
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, 1200)")
            time.sleep(3)

            # 🔥 ambil semua tombol
            buttons = driver.find_elements(By.CSS_SELECTOR, "a.mod-btn")

            print("Jumlah tombol ditemukan:", len(buttons))

            if len(buttons) == 0:
                print("Tombol belum muncul, retry...")
                time.sleep(3)
                continue

            for btn in buttons:
                val = btn.get_attribute("data-value")
                print("Ditemukan tombol:", val)

                if val == model_value:
                    print("Klik model:", model_name)

                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(2)

                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(5)

                    success = True
                    break

            if success:
                break

        except Exception as e:
            print("Error klik model:", e)
            time.sleep(3)

    if not success:
        print("Model gagal total:", model_name)
        continue

    panels = driver.find_elements(By.CSS_SELECTOR,"div.panel.panel-days")

    for panel in panels:

        try:

            header = panel.find_element(By.CSS_SELECTOR,"div.panel-body.pointer")

            jam_text = header.text.split("\n")[0]
            jam = jam_text.split("-")[0].strip()

            if jam not in TARGET_JAM:
                continue

            print("Ambil jam:",jam)

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", header)
            time.sleep(1)

            driver.execute_script("arguments[0].click();", header)

            filename = f"{model_name}_{jam}.png".replace(":", "")
            driver.save_screenshot(filename)
            print("Screenshot:", filename)

            detail = panel.find_element(By.CSS_SELECTOR,"div.daytable-detail")

            panel_text = detail.text

            temperature,humidity,rain,wind = ambil_data_panel(panel_text)

            data_all.append([
                model_name,
                jam,
                temperature,
                humidity,
                rain,
                wind
            ])

            time.sleep(1)

        except Exception as e:
            print("gagal ambil jam",e)


driver.quit()

# =========================================
# DEBUG: SIMPAN DATA SEBELUM FILTER
# =========================================

with open("forecast_raw.csv","w",newline="",encoding="utf8") as f:
    writer = csv.writer(f)
    writer.writerow(["Model","Jam","Temperature","Humidity","Rain","Wind"])
    writer.writerows(data_all)

print("DEBUG → forecast_raw.csv tersimpan")


data_filtered = []

grouped = defaultdict(list)

for row in data_all:
    grouped[row[0]].append(row)

# =========================================
# DEBUG: SIMPAN DATA PER MODEL (BELUM FILTER INDEX)
# =========================================

with open("forecast_per_model_raw.csv","w",newline="",encoding="utf8") as f:
    writer = csv.writer(f)
    writer.writerow(["Model","Jam","Temperature","Humidity","Rain","Wind"])

    for model in grouped:
        for row in grouped[model]:
            writer.writerow(row)

print("DEBUG → forecast_per_model_raw.csv tersimpan")

def normalize_jam(j):
        return j.replace(" ", "").lower()

for model in grouped:
    data_model = grouped[model]

    

    mapping = {normalize_jam(row[1]): row for row in data_model}

    selected = []
    for jam in TARGET_JAM:
        jam_norm = normalize_jam(jam)

        if jam_norm in mapping:
            selected.append(mapping[jam_norm])
        else:
            print(f"{model} → jam {jam} tidak ditemukan")

    if len(selected) == len(TARGET_JAM):
        data_filtered.extend(selected)
    else:
        print(f"Data {model} tidak lengkap sesuai TARGET_JAM")
        data_filtered.extend(selected)

# =========================================
# DEBUG: SIMPAN DATA SETELAH FILTER
# =========================================

with open("forecast_filtered_debug.csv","w",newline="",encoding="utf8") as f:
    writer = csv.writer(f)
    writer.writerow(["Model","Jam","Temperature","Humidity","Rain","Wind"])
    writer.writerows(data_filtered)

print("DEBUG → forecast_filtered_debug.csv tersimpan")

with open("forecast_dago.csv","w",newline="",encoding="utf8") as f:

    writer = csv.writer(f)

    writer.writerow([
        "Model",
        "Jam",
        "Temperature",
        "Humidity",
        "Rain",
        "Wind"
    ])

    writer.writerows(data_filtered)

print("Selesai → forecast_dago.csv")


# =========================================
# ============== ENSEMBLE (FIX) ===========
# =========================================

import math
import re

def parse_temp(t):
    return float(re.findall(r"\d+\.?\d*", t)[0])

def parse_rh(r):
    return float(re.findall(r"\d+", r)[0])

def parse_rain(r):
    return float(re.findall(r"\d+\.?\d*", r)[0])

def convert_jam(j):
    j = j.strip().lower()
    try:
        return datetime.strptime(j,"%I:%M%p").strftime("%H:%M")
    except:
        pass
    match = re.match(r"(\d{1,2}):(\d{2})(am|pm)", j)
    if match:
        h = int(match.group(1))
        m = match.group(2)
        ap = match.group(3)
        if ap == "pm" and h != 12: h += 12
        if ap == "am" and h == 12: h = 0
        return f"{h:02d}:{m}"
    return j


def kategori_hujan(mm):
    if mm == 0: return "Berawan"
    elif mm <= 5: return "Hujan Ringan"
    elif mm <= 10: return "Hujan Sedang"
    else: return "Hujan Lebat"

def bmkg_to_kategori(cuaca):
    cuaca = cuaca.lower()

    if "hujan lebat" in cuaca:
        return "Hujan Lebat"
    elif "hujan sedang" in cuaca:
        return "Hujan Sedang"
    elif "hujan ringan" in cuaca:
        return "Hujan Ringan"
    else:
        return "Berawan"

bmkg_data = {}
with open("bmkg_dago.csv") as f:
    for row in csv.DictReader(f):
        cuaca = row["cuaca"]

        bmkg_data[row["jam"].strip()] = {
            "temp": float(row["suhu_C"]),
            "rh": float(row["RH_%"]),
            "kategori": bmkg_to_kategori(cuaca)
}


forecast_data = defaultdict(list)

with open("forecast_dago.csv") as f:
    for row in csv.DictReader(f):
        try:
            jam = convert_jam(row["Jam"]).strip()
            forecast_data[jam].append({
                "temp": parse_temp(row["Temperature"]),
                "rh": parse_rh(row["Humidity"]),
                "rain": parse_rain(row["Rain"])
            })
        except Exception as e:
            print("ERROR:", row, e)


def mean_std(v):
    if not v: return None,None
    m = sum(v)/len(v)
    s = math.sqrt(sum((x-m)**2 for x in v)/len(v))
    return round(m,2), round(s,2)

def heat_index(T, RH):
    # Rumus Heat Index (NOAA, dalam Celsius)
    HI = -8.784695 \
         + 1.61139411*T \
         + 2.338549*RH \
         - 0.14611605*T*RH \
         - 0.012308094*(T**2) \
         - 0.016424828*(RH**2) \
         + 0.002211732*(T**2)*RH \
         + 0.00072546*T*(RH**2) \
         - 0.000003582*(T**2)*(RH**2)

    return round(HI, 2)

ensemble = []

for jam in sorted(set(bmkg_data) | set(forecast_data)):

    temp, rh, rain, hi_list = [],[],[],[]
    count = defaultdict(int)

    if jam in bmkg_data:
        temp.append(bmkg_data[jam]["temp"])
        rh.append(bmkg_data[jam]["rh"])
        rain.append(0.0)  # boleh tetap 0 kalau tidak pakai mm
        hi_list.append(heat_index(
        bmkg_data[jam]["temp"],
        bmkg_data[jam]["rh"]
        ))

        kategori = bmkg_data[jam]["kategori"]
        count[kategori] += 1

    for d in forecast_data.get(jam,[]):
        temp.append(d["temp"])
        rh.append(d["rh"])
        rain.append(d["rain"])
        count[kategori_hujan(d["rain"])] += 1
        hi_list.append(heat_index(d["temp"], d["rh"]))

    total = sum(count.values())
    prob = {k: round(v/total*100,1) for k,v in count.items()}

    t_mean,t_std = mean_std(temp)
    r_mean,r_std = mean_std(rh)
    p_mean,p_std = mean_std(rain)
    hi_mean, hi_std = mean_std(hi_list)

 


    ensemble.append([
        jam,
        t_mean,f"±{t_std}",
        r_mean,f"±{r_std}",
        p_mean,f"±{p_std}",
        hi_mean, f"±{hi_std}",
        prob.get("Berawan",0),
        prob.get("Hujan Ringan",0),
        prob.get("Hujan Sedang",0),
        prob.get("Hujan Lebat",0)
    ])

today = datetime.now().strftime("%Y%m%d")

with open(f"ensemble_dago_{today}.csv","w",newline="",encoding="utf8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "jam",
        "temp_mean","temp_error",
        "rh_mean","rh_error",
        "rain_mean","rain_error",
        "heat_index_mean","heat_index_error",
        "%berawan",
        "%hujan_ringan",
        "%hujan_sedang",
        "%hujan_lebat"
    ])
    writer.writerows(ensemble)

print(f"\nENSEMBLE SUKSES → ensemble_dago_{today}.csv\n")

# =========================================
# ===== CSV KHUSUS CANVA (1 HARI 1 BARIS) ==
# =========================================

import csv

# baca hasil ensemble
with open(f"ensemble_dago_{today}.csv") as f:
    data = list(csv.DictReader(f))

# siapkan 1 baris
row = {}

for i, d in enumerate(data):
    idx = i + 1

    row[f"jam{idx}"] = d["jam"]
    row[f"temp{idx}"] = d["temp_mean"]
    row[f"rh{idx}"] = d["rh_mean"]
    row[f"hi{idx}"] = f"{d['heat_index_mean']} ± {d['heat_index_error']}"
    row[f"hujan_ringan{idx}"] = d["%hujan_ringan"]

# simpan CSV baru
with open("canva_dago.csv","w",newline="",encoding="utf8") as f:
    writer = csv.DictWriter(f, fieldnames=row.keys())
    writer.writeheader()
    writer.writerow(row)

print("CSV Canva siap → canva_dago.csv")
