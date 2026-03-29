import streamlit as st
from google import genai  # 【修改 1】：使用最新版 Google GenAI 套件
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="智能餐廳推薦系統", page_icon="🍽️", layout="centered")

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

st.title("🍽️ 智能餐廳推薦系統")
st.write("肚子餓了嗎？設定好你的條件，讓我幫你找出最棒的餐廳！")

# ==========================================
# 模組 1：使用者輸入模組 (側邊欄)
# ==========================================
st.sidebar.header("⚙️ 設定搜尋條件")

st.sidebar.subheader("📍 你的位置")
manual_location = st.sidebar.text_input("手動輸入地址或地標", placeholder="例如：台中市太平區...")

with st.sidebar:
    st.write("或使用 GPS 自動定位：")
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

# 【修改 3】：把舊版的 use_container_width=True 換成最新的 width="stretch"
if st.button("🚀 開始搜尋餐廳", width="stretch"):
    errors = []
    
    if location_display == "尚未設定":
        errors.append("請在左側輸入位置，或點擊定位按鈕！")
    
    if budget is None or budget <= 0:
        errors.append("請輸入大於 0 的預算上限！")

    if errors:
        for error in errors:
            st.warning(f"⚠️ {error}")
    else:
        st.success("條件設定完成！開始搜尋並過濾餐廳...")
        
        # ==========================================
        # 模組 2：餐廳資料取得模組 (假資料)
        # ==========================================
        mock_restaurants = [
            {"name": "巷口麵攤", "cuisine": "台灣傳統小吃", "price": 80, "rating": 4.2, "distance": 300, "options": ["不吃海鮮", "不吃辣", "不吃香菜"]},
            {"name": "豪華牛排館", "cuisine": "美式高級排餐", "price": 1200, "rating": 4.8, "distance": 2500, "options": ["不吃海鮮", "不吃香菜"]},
            {"name": "健康蔬食坊", "cuisine": "創意素食料理", "price": 250, "rating": 4.5, "distance": 800, "options": ["素食", "不吃海鮮", "不吃辣", "不吃香菜"]},
            {"name": "地獄麻辣鍋", "cuisine": "四川麻辣火鍋", "price": 600, "rating": 4.6, "distance": 1500, "options": ["不吃香菜"]},
            {"name": "阿明海鮮快炒", "cuisine": "台灣在地熱炒", "price": 400, "rating": 3.9, "distance": 1200, "options": ["不吃辣"]},
            {"name": "義式無麩質餐廳", "cuisine": "義大利麵與披薩", "price": 800, "rating": 4.3, "distance": 3500, "options": ["無麩質", "不吃辣", "不吃海鮮", "不吃香菜"]},
            {"name": "太平老街臭豆腐", "cuisine": "台灣特色小吃", "price": 60, "rating": 4.1, "distance": 150, "options": ["不吃海鮮"]},
            {"name": "頂級日式壽司", "cuisine": "日式料理與壽司", "price": 1500, "rating": 4.9, "distance": 4000, "options": ["不吃辣", "不吃香菜"]},
            {"name": "小清新早午餐", "cuisine": "西式輕食與咖啡", "price": 300, "rating": 4.4, "distance": 600, "options": ["不吃海鮮", "不吃辣", "無麩質"]},
            {"name": "香辣泰式料理", "cuisine": "泰國菜", "price": 500, "rating": 4.0, "distance": 2000, "options": ["不吃海鮮"]}
        ]
        
        # ==========================================
        # 模組 5：條件過濾模組
        # ==========================================
        filtered_restaurants = []
        for r in mock_restaurants:
            if r["price"] > budget:
                continue 
            if r["distance"] > distance:
                continue 
            
            can_eat = True
            for req in restrictions: 
                if req not in r["options"]:
                    can_eat = False  
                    break            
            
            if not can_eat:
                continue 
                
            filtered_restaurants.append(r)
            
        # ==========================================
        # 模組 3 & 4：資料處理與推薦演算法模組
        # ==========================================
        if len(filtered_restaurants) > 0:
            prices = [r["price"] for r in filtered_restaurants]
            distances = [r["distance"] for r in filtered_restaurants]
            ratings = [r["rating"] for r in filtered_restaurants]
            
            max_p, min_p = max(prices), min(prices)
            max_d, min_d = max(distances), min(distances)
            max_r, min_r = max(ratings), min(ratings)
            
            def normalize(val, min_v, max_v, reverse=False):
                if max_v == min_v:  
                    return 1.0
                if reverse: 
                    return (max_v - val) / (max_v - min_v)
                else:       
                    return (val - min_v) / (max_v - min_v)

            for r in filtered_restaurants:
                score_rating = normalize(r["rating"], min_r, max_r, reverse=False)
                score_dist = normalize(r["distance"], min_d, max_d, reverse=True)
                score_price = normalize(r["price"], min_p, max_p, reverse=True)
                score_pref = 1.0
                
                final_score = (score_rating * 0.4) + (score_dist * 0.3) + (score_price * 0.2) + (score_pref * 0.1)
                r["推薦分數"] = round(final_score * 100, 1)

            filtered_restaurants.sort(key=lambda x: x["推薦分數"], reverse=True)
            
            st.success("🎉 計算完成！以下是為您量身打造的推薦清單：")
            
            # ==========================================
            # 模組 6：AI 菜單推薦模組 (專注於第 1 名)
            # ==========================================
            top1 = filtered_restaurants[0]
            
            diet_str = ', '.join(restrictions) if restrictions else "無特殊忌口"
            prompt = f"""
            你是一位美食評論家。使用者今天來到一間叫做「{top1['name']}」的餐廳。
            這間餐廳的風格是：{top1['cuisine']}。
            使用者的飲食忌口或限制是：{diet_str}。

            請根據以上資訊，為使用者生成一份包含「前菜」、「主餐」、「飲品」、「甜點」的專屬餐點組合推薦。
            生成的格式必須是 Markdown 語法，並且：
            1. 語氣要專業且富有食慾，能吸引使用者。
            2. 餐點必須嚴格遵守飲食忌口條件（如果忌口是無麩質，絕對不能出現麵條）。
            3. 每道餐點請附上一句簡單的中文推薦理由。
            """
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 2]) 
                
                with col1:
                    st.subheader("🥇 第一名推薦")
                    st.metric(label=top1['name'], value=f"{top1['推薦分數']} 分")
                    st.write(f"- **風格**：{top1['cuisine']}")
                    st.write(f"- **距離**：{top1['distance']}m")
                    st.write(f"- **預算**：${top1['price']}")
                    st.write(f"- **評分**：⭐️ {top1['rating']}")

                with col2:
                    st.write("#### ✨ AI 特選專屬菜單")
                    with st.spinner(f"正在請 AI 分析「{top1['cuisine']}」菜單..."):
                        try:
                            # 【修改 4】：使用新版 SDK 呼叫 generate_content，並指定升級的 gemini-2.5-flash 模型
                            response = ai_client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=prompt
                            )
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"菜單生成失敗，請檢查 API 金鑰或網路。錯誤訊息: {e}")

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
                            st.caption(f"風格：{runner_ups[i]['cuisine']} | 評分：⭐️ {runner_ups[i]['rating']}")
                
            st.markdown("---")
            st.write("#### 📋 完整推薦排行榜")
            display_data = [
                {
                    "名次": idx + 1,
                    "餐廳名稱": r["name"], 
                    "風格": r["cuisine"],
                    "推薦分數": r["推薦分數"], 
                    "評分": r["rating"], 
                    "價格": r["price"], 
                    "距離(m)": r["distance"]
                } 
                for idx, r in enumerate(filtered_restaurants)
            ]
            
            # 【修改 5】：把舊版的 use_container_width=True 換成最新的 width="stretch"
            st.dataframe(display_data, width="stretch", hide_index=True)
            
        else:
            st.warning("🥲 糟糕，沒有任何餐廳符合您的嚴格條件，請嘗試放寬預算或距離！")