import streamlit as st
from google import genai  # 【修改 1】：使用最新版 Google GenAI 套件
from streamlit_geolocation import streamlit_geolocation
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="爆吃AI 智能餐廳推薦系統", page_icon="👽", layout="centered")

# ==========================================
# 隱藏 Streamlit 預設介面 (選單、Deploy、頁尾)
# ==========================================
hide_streamlit_style = """
<style>
/* 隱藏右上角的 Deploy 按鈕與主選單 */
[data-testid="stToolbar"] {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* 隱藏最下方的 "Made with Streamlit" 頁尾 */
footer {visibility: hidden !important;}

/* 隱藏最頂部的裝飾彩條 (可選，讓畫面更乾淨) */
header {visibility: hidden !important;}
</style>
# """
# 透過 st.markdown 強制寫入 HTML 與 CSS 語法
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# AI 設定與金鑰讀取
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    # 【修改 2】：使用新版 SDK 的 Client 初始化寫法
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error("⚠️ AI 金鑰設定失敗，請檢查 .streamlit/secrets.toml 檔案！")
    st.stop()

st.title("👽 爆吃AI 智能餐廳推薦系統")
st.write("肚子餓了嗎？設定好你的條件，讓我幫你找出最棒的餐廳！")

# ==========================================
# 模組 1：使用者輸入模組 (側邊欄)
# ==========================================
st.sidebar.header("⚙️ 設定搜尋條件")

st.sidebar.subheader("📍 你的位置")
manual_location = st.sidebar.text_input("手動輸入地址或地標", placeholder="例如：台中市北屯區...")

with st.sidebar:
    st.write("或按下按鈕使用 GPS 自動定位：")
    location = streamlit_geolocation()

location_display = "尚未設定"
if location and location.get('latitude') is not None:
    lat = location['latitude']
    lon = location['longitude']
    location_display = f"GPS 定位 (緯度: {lat:.4f}, 經度: {lon:.4f})"
elif manual_location:
    location_display = f"手動輸入 ({manual_location})"

st.sidebar.markdown("---")

budget = st.sidebar.number_input(
    "預算上限 (元)", 
    min_value=0,      
    step=50,          
    value=None,       
    placeholder="請輸入預算數字..."
)

distance = st.sidebar.slider("願意移動的最大距離 (公尺)", min_value=100, max_value=5000, value=1000, step=100)

restrictions = st.sidebar.multiselect(
    "飲食忌口或偏好 (可多選)",
    ["不吃辣", "素食", "不吃海鮮", "不吃香菜", "無麩質"]
)

# ==========================================
# 主畫面：顯示確認資訊與搜尋按鈕
# ==========================================
st.subheader("📋 目前的搜尋條件")

budget_display = f"{budget} 元" if budget is not None else "尚未輸入"

st.write(f"- **目前位置**：{location_display}")
st.write(f"- **預算上限**：{budget_display}")
st.write(f"- **最大距離**：{distance} 公尺")
st.write(f"- **忌口條件**：{', '.join(restrictions) if restrictions else '無'}")

st.markdown("---")

# ==========================================
# 【新增】：建立網頁專屬的「記憶體」
# ==========================================
# 只要網頁還開著，存在 session_state 裡面的東西就不會消失
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False  # 記錄「有沒有按過搜尋按鈕」
if "ai_menu" not in st.session_state:
    st.session_state.ai_menu = None          # 記錄「AI 產生的菜單文字」

# ==========================================
# 按鈕區塊：現在只負責「檢查」跟「打開開關」
# ==========================================
if st.button("🚀 開始搜尋餐廳", width="stretch"):
    errors = []
    
    if location_display == "尚未設定":
        errors.append("請在左側輸入位置，或點擊定位按鈕！")
    if budget is None or budget <= 0:
        errors.append("請輸入大於 0 的預算上限！")

    if errors:
        for error in errors:
            st.warning(f"⚠️ {error}")
        # 如果有錯，就把開關關掉
        st.session_state.search_clicked = False
    else:
        # 【關鍵】：檢查通過！把開關打開，並清空上一筆 AI 菜單的記憶
        st.session_state.search_clicked = True
        st.session_state.ai_menu = None


# ==========================================
# 核心邏輯區塊：只要開關是打開的，就顯示結果
# ==========================================
# 注意：這裡的 if 是看記憶體裡的開關，而不是看按鈕！
if st.session_state.search_clicked:
    
    # ==========================================
    # 模組 2：餐廳資料取得模組 (高度擬真 Demo 版 - 台中精選)
    # ==========================================
    # 1. 決定搜尋的中心點座標
    search_lat, search_lon = None, None
    if location and location.get('latitude') is not None:
        search_lat = location['latitude']
        search_lon = location['longitude']
    elif manual_location:
        # 手動輸入地址時，借用免費的 Nominatim API 轉經緯度
        with st.spinner("正在解析地址座標..."):
            try:
                import requests
                geo_url = "https://nominatim.openstreetmap.org/search"
                geo_res = requests.get(geo_url, params={'q': manual_location, 'format': 'json', 'limit': 1}, headers={'User-Agent': 'MyRestaurantApp'})
                if geo_res.json():
                    search_lat = float(geo_res.json()[0]['lat'])
                    search_lon = float(geo_res.json()[0]['lon'])
            except Exception as e:
                pass

    if search_lat is None or search_lon is None:
        st.error("❌ 無法取得有效的經緯度，請確認定位或輸入更詳細的地址！")
        st.session_state.search_clicked = False
        st.stop()

    # 2. 計算兩點距離的函式 (Haversine 公式)
    import math
    def calculate_distance(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return int(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a))))

    # 3. 高度擬真的台中市餐廳資料庫 (刪除 cuisine 欄位)
    with st.spinner("正在載入精選餐廳資料庫..."):
        demo_database = [
            {"name": "屋馬燒肉 (國安店)", "price": 1500, "rating": 4.8, "lat": 24.192, "lon": 120.603, "options": ["不吃海鮮", "不吃香菜", "不吃辣"], "reviews": "雞湯超好喝可以無限續，海鮮粥必點，肉質鮮嫩服務極佳！"},
            {"name": "輕井澤鍋物 (文心南二店)", "price": 400, "rating": 4.5, "lat": 24.131, "lon": 120.647, "options": ["不吃辣", "不吃海鮮", "不吃香菜", "無麩質"], "reviews": "裝潢大氣，壽喜燒湯頭偏甜很下飯，紅茶好喝，CP值極高。"},
            {"name": "赤鬼炙燒牛排 (台灣大道店)", "price": 380, "rating": 4.2, "lat": 24.156, "lon": 120.654, "options": ["不吃海鮮", "不吃香菜"], "reviews": "酥脆麵包跟羅宋湯很讚，牛排份量大，黑胡椒醬夠味。"},
            {"name": "宮原眼科", "price": 250, "rating": 4.4, "lat": 24.137, "lon": 120.683, "options": ["素食", "不吃海鮮", "不吃辣", "不吃香菜", "無麩質"], "reviews": "冰淇淋口味超多，巧克力系列必吃，還可以免費加鳳梨酥跟乳酪蛋糕！"},
            {"name": "沁園春", "price": 800, "rating": 4.3, "lat": 24.138, "lon": 120.683, "options": ["不吃辣", "不吃海鮮"], "reviews": "小籠包皮薄汁多，排骨炒飯粒粒分明，老字號招牌玫瑰包必點。"},
            {"name": "刁民酸菜魚 (逢甲店)", "price": 600, "rating": 4.6, "lat": 24.176, "lon": 120.645, "options": ["不吃海鮮", "不吃香菜"], "reviews": "湯頭酸爽麻辣超級下飯！洛神花茶解辣神物，裡面加點老油條超好吃。"},
            {"name": "飪室咖哩 RenshiCurry", "price": 300, "rating": 4.5, "lat": 24.148, "lon": 120.655, "options": ["不吃海鮮", "無麩質"], "reviews": "初戀咖哩帶點番茄酸甜，起司烤餅拉絲超浮誇，裝潢很網美。"},
            {"name": "老向的店", "price": 120, "rating": 4.4, "lat": 24.172, "lon": 120.680, "options": ["不吃海鮮", "不吃辣"], "reviews": "清蒸鴨腿麵晚來吃不到！蒜泥白肉份量多，平價吃粗飽的神店。"},
            {"name": "茶六燒肉堂 (朝富店)", "price": 1600, "rating": 4.7, "lat": 24.164, "lon": 120.636, "options": ["不吃海鮮", "不吃香菜", "不吃辣"], "reviews": "鮭魚味噌湯料超多，鹽蔥牛舌絕配，最後的雪花冰是完美結尾。"},
            {"name": "斐得蔬食", "price": 450, "rating": 4.8, "lat": 24.140, "lon": 120.665, "options": ["素食", "不吃海鮮", "不吃辣", "不吃香菜"], "reviews": "完全吃不出是素食！松露燉飯香氣濃郁，植物肉漢堡排口感驚豔。"}
        ]
        
        # 即時計算這 10 間餐廳與你目前位置的距離
        real_restaurants = []
        for r in demo_database:
            r["distance"] = calculate_distance(search_lat, search_lon, r["lat"], r["lon"])
            real_restaurants.append(r)

    # ------------------------------------------
    # 模組 5：過濾模組
    # ------------------------------------------
    filtered_restaurants = []
    for r in real_restaurants:  
        if r["price"] > budget: continue 
        if r["distance"] > distance: continue 
        can_eat = True
        for req in restrictions: 
            if req not in r["options"]:
                can_eat = False  
                break            
        if not can_eat: continue 
        filtered_restaurants.append(r)
        
    # ------------------------------------------
    # 模組 3 & 4：算分邏輯
    # ------------------------------------------
    if len(filtered_restaurants) > 0:
        prices = [r["price"] for r in filtered_restaurants]
        distances = [r["distance"] for r in filtered_restaurants]
        ratings = [r["rating"] for r in filtered_restaurants]
        max_p, min_p = max(prices), min(prices)
        max_d, min_d = max(distances), min(distances)
        max_r, min_r = max(ratings), min(ratings)
        
        def normalize(val, min_v, max_v, reverse=False):
            if max_v == min_v: return 1.0
            if reverse: return (max_v - val) / (max_v - min_v)
            else: return (val - min_v) / (max_v - min_v)

        for r in filtered_restaurants:
            score_rating = normalize(r["rating"], min_r, max_r, reverse=False)
            score_dist = normalize(r["distance"], min_d, max_d, reverse=True)
            score_price = normalize(r["price"], min_p, max_p, reverse=True)
            final_score = (score_rating * 0.4) + (score_dist * 0.3) + (score_price * 0.2) + 0.1
            r["推薦分數"] = round(final_score * 100, 1)

        filtered_restaurants.sort(key=lambda x: x["推薦分數"], reverse=True)
        st.success("🎉 計算完成！以下是為您量身打造的推薦清單：")
        
        # ------------------------------------------
        # 模組 6：AI 菜單 (結合真實評論生成)
        # ------------------------------------------
        top1 = filtered_restaurants[0]
        diet_str = ', '.join(restrictions) if restrictions else "無特殊忌口"
        
        # 移除風格，保留評價
        prompt = f"""
        你是一位專業的美食推薦嚮導。使用者今天來到一間叫做「{top1['name']}」的餐廳。
        網友對這家店的真實評價是：「{top1['reviews']}」
        使用者的飲食忌口或限制是：{diet_str}。

        請根據以上資訊，為使用者生成一份專屬餐點推薦。
        
        1. 語氣要專業且富有食慾，能吸引使用者。
        2. 請「務必」將網友評價中提到的招牌菜色融入菜單中（如果符合忌口條件）。
        3. 必須包含「前菜」、「主餐」、「飲品」、「甜點」。
        4. 嚴格遵守飲食忌口條件（例如不吃海鮮就絕對不能推薦海鮮粥）。
        """
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 2]) 
            with col1:
                st.subheader("🥇 第一名推薦")
                st.metric(label="本站推薦分數", value=f"{top1['推薦分數']} 分")
                
                # 移除了風格顯示
                st.write(f"- **餐廳名稱**：{top1['name']}")
                st.write(f"- **預算**：${top1['price']}")
                st.write(f"- **距離**：{top1['distance']}m")
                st.write(f"- **真實評分**：⭐️ {top1['rating']} / 5.0")
                st.info(f"💬 **網友評價**：{top1['reviews']}") 

            with col2:
                st.write("#### ✨ AI 特選專屬菜單")
                
                if st.session_state.ai_menu is None:
                    # 動畫文字改為顯示餐廳名稱
                    with st.spinner(f"正在請 AI 分析「{top1['name']}」菜單..."):
                        try:
                            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                            st.session_state.ai_menu = response.text
                        except Exception as e:
                            st.error(f"菜單生成失敗: {e}")
                
                if st.session_state.ai_menu:
                    st.markdown(st.session_state.ai_menu)

        # ------------------------------------------
        # 其他名次與表格
        # ------------------------------------------
        if len(filtered_restaurants) > 1:
                st.markdown("### 🥈 其他優質選擇")
                runner_ups = filtered_restaurants[1:3] 
                cols = st.columns(len(runner_ups))
                
                for i, col in enumerate(cols):
                    with col:
                        with st.container(border=True):
                            st.metric(label=f"第 {i+2} 名：{runner_ups[i]['name']}", 
                                      value=f"{runner_ups[i]['推薦分數']} 分", 
                                      delta=f"{runner_ups[i]['distance']}m | {runner_ups[i]['price']}元",
                                      delta_color="off")
                            st.caption(f"⭐️ 真實評分：{runner_ups[i]['rating']}")
                            st.write(f"💬 {runner_ups[i]['reviews']}")
            
        st.markdown("---")
        st.write("#### 📋 完整推薦排行榜")
        display_data = [
                {
                    "名次": idx + 1,
                    "餐廳名稱": r["name"], 
                    "推薦分數": f"{r['推薦分數']} 分",  
                    "真實評分": f"⭐️ {r['rating']}",   
                    "網友評價": r["reviews"],          
                    "價格": f"${r['price']}", 
                    "距離(m)": r["distance"]
                } 
                for idx, r in enumerate(filtered_restaurants)
            ]
        # 這裡的 hide_index=True 讓表格左側更乾淨
        st.dataframe(display_data, width="stretch", hide_index=True)
        
        # ------------------------------------------
        # 模組 7：地圖顯示 (原封不動)
        # ------------------------------------------
        st.markdown("---")
        st.markdown("### 🗺️ 推薦餐廳地圖分佈")
        if location and location.get('latitude') is not None:
            center_lat, center_lon = location['latitude'], location['longitude']
        else:
            center_lat, center_lon = top1["lat"], top1["lon"]

        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

        if location and location.get('latitude') is not None:
            folium.Marker([location['latitude'], location['longitude']], popup="📍 你的目前位置", tooltip="我的位置", icon=folium.Icon(color="red", icon="info-sign")).add_to(m)

        for idx, r in enumerate(filtered_restaurants):
            marker_color = "orange" if idx == 0 else "blue"
            icon_type = "star" if idx == 0 else "cutlery"
            html_popup = f"<b>{r['name']}</b><br>分數: {r['推薦分數']}<br>價格: {r['price']}元"
            folium.Marker([r["lat"], r["lon"]], popup=html_popup, tooltip=f"第 {idx+1} 名：{r['name']}", icon=folium.Icon(color=marker_color, icon=icon_type)).add_to(m)

        st_folium(m, width="100%", height=500)
        
    else:
        st.warning("🥲 糟糕，沒有任何餐廳符合您的嚴格條件，請嘗試放寬預算或距離！")