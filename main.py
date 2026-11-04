
import streamlit as st
import pandas as pd
import folium
import numpy as np

from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="우리 학교 주변 상권 분석",
    page_icon="📍",
    layout="wide"
)

# --------------------------------------------------
# 2. 디자인 CSS
# --------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.stApp {
    background-color: #F5F7FB;
}

.main-title {
    font-size: 34px;
    font-weight: 800;
    color: #172B4D;
    margin-bottom: 5px;
}

.sub-title {
    color: #75839A;
    font-size: 15px;
    margin-bottom: 25px;
}

.section-title {
    font-size: 22px;
    font-weight: 800;
    color: #203451;
    margin-top: 20px;
    margin-bottom: 12px;
}

.stat-card {
    background: white;
    border-radius: 15px;
    padding: 20px;
    border: 1px solid #E5EAF2;
    box-shadow: 0 3px 12px rgba(0,0,0,0.03);
}

.stat-label {
    color: #8290A5;
    font-size: 14px;
}

.stat-value {
    color: #1C3557;
    font-size: 27px;
    font-weight: 800;
    margin-top: 5px;
}

.result-card {
    background: white;
    border-radius: 16px;
    padding: 25px;
    border: 1px solid #E5EAF2;
    margin-top: 15px;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #E5EAF2;
}

.stButton button {
    border-radius: 10px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 제목
# --------------------------------------------------

st.markdown(
    '<div class="main-title">📍 우리 학교 주변 상권 분석</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">DATA-DRIVEN COMMERCIAL LOCATION ANALYSIS | 데이터 기반 입지 분석</div>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# 4. CSV 업로드
# --------------------------------------------------

st.sidebar.title("⚙️ 데이터 설정")

uploaded_file = st.sidebar.file_uploader(
    "공공데이터 CSV 파일 업로드",
    type=["csv"]
)

st.sidebar.caption(
    "상호명, 상권업종소분류명, 위도, 경도 데이터가 필요합니다."
)

if uploaded_file is None:
    st.title("데이터를 업로드해 주세요!")
    st.info(
        "공공데이터포털에서 다운로드한 상권 CSV 파일을 "
        "왼쪽 메뉴에서 업로드하면 분석이 시작됩니다."
    )

    st.markdown("### 📂 필요한 데이터")
    st.write("- 상호명")
    st.write("- 상권업종소분류명")
    st.write("- 위도")
    st.write("- 경도")

    st.stop()

# --------------------------------------------------
# 5. CSV 읽기 (한글 인코딩 자동 대응)
# --------------------------------------------------

@st.cache_data
def load_csv(file_bytes):
    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]

    for encoding in encodings:
        try:
            import io
            return pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding
            )
        except (UnicodeDecodeError, UnicodeError):
            continue

    raise ValueError("CSV 파일의 인코딩을 확인할 수 없습니다.")

try:
    df = load_csv(uploaded_file.getvalue())

except Exception as e:
    st.error(f"파일을 읽을 수 없습니다: {e}")
    st.stop()

# --------------------------------------------------
# 6. 컬럼 자동 인식
# --------------------------------------------------

def find_column(columns, candidates):
    for candidate in candidates:
        for col in columns:
            if str(col).strip() == candidate:
                return col

    return None

name_col = find_column(
    df.columns,
    ["상호명", "사업장명", "업소명", "점포명"]
)

category_col = find_column(
    df.columns,
    ["상권업종소분류명", "업종소분류명", "업종명"]
)

lat_col = find_column(
    df.columns,
    ["위도", "LAT", "latitude"]
)

lon_col = find_column(
    df.columns,
    ["경도", "LON", "longitude"]
)

required = {
    "상호명": name_col,
    "상권업종소분류명": category_col,
    "위도": lat_col,
    "경도": lon_col
}

missing = [
    key for key, value in required.items()
    if value is None
]

if missing:
    st.error(
        "필요한 컬럼을 찾을 수 없습니다: "
        + ", ".join(missing)
    )
    st.write("현재 CSV 컬럼:", list(df.columns))
    st.stop()

# --------------------------------------------------
# 7. 데이터 전처리
# --------------------------------------------------

df = df.copy()

df["상호명"] = df[name_col].fillna("이름 없음").astype(str)
df["업종"] = df[category_col].fillna("업종 미분류").astype(str)

df["위도"] = pd.to_numeric(df[lat_col], errors="coerce")
df["경도"] = pd.to_numeric(df[lon_col], errors="coerce")

df = df.dropna(
    subset=["위도", "경도", "업종"]
)

df = df[
    df["위도"].between(-90, 90)
    & df["경도"].between(-180, 180)
].copy()

if df.empty:
    st.error("지도에 표시할 수 있는 위치 데이터가 없습니다.")
    st.stop()

# --------------------------------------------------
# 8. 통계 계산
# --------------------------------------------------

total_count = len(df)

category_counts = (
    df.groupby("업종")
    .size()
    .sort_values(ascending=False)
)

category_count = len(category_counts)

top_category = category_counts.index[0]

# --------------------------------------------------
# 9. 상단 통계 카드
# --------------------------------------------------

st.markdown('<div class="section-title">📊 상권 현황 요약</div>',
            unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("전체 점포 수", f"{total_count:,}개")

with c2:
    st.metric("업종 종류", f"{category_count:,}개")

with c3:
    st.metric("가장 많은 업종", top_category)

with c4:
    st.metric(
        "분석 데이터",
        "CSV",
        help="업로드한 공공데이터를 기준으로 분석합니다."
    )

# --------------------------------------------------
# 10. 지도 영역
# --------------------------------------------------

st.markdown(
    '<div class="section-title">🗺️ 학교 주변 상권 지도</div>',
    unsafe_allow_html=True
)

categories = ["전체 업종"] + sorted(df["업종"].unique().tolist())

selected_map_category = st.selectbox(
    "지도에 표시할 업종을 선택하세요.",
    categories
)

if selected_map_category == "전체 업종":
    map_df = df.copy()
else:
    map_df = df[
        df["업종"] == selected_map_category
    ].copy()

center_lat = float(map_df["위도"].mean())
center_lon = float(map_df["경도"].mean())

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15,
    tiles="CartoDB positron"
)

marker_cluster = MarkerCluster().add_to(m)

for _, row in map_df.iterrows():

    popup_text = f"""
    <div style="width:180px">
        <b>{row['상호명']}</b><br>
        업종: {row['업종']}<br>
        위도: {row['위도']:.5f}<br>
        경도: {row['경도']:.5f}
    </div>
    """

    folium.Marker(
        location=[row["위도"], row["경도"]],
        tooltip=row["상호명"],
        popup=folium.Popup(popup_text, max_width=250),
        icon=folium.Icon(
            color="blue",
            icon="shopping-cart",
            prefix="fa"
        )
    ).add_to(marker_cluster)

st_folium(
    m,
    width=None,
    height=580,
    use_container_width=True,
    returned_objects=[]
)

st.caption(
    f"현재 지도에 표시된 점포: {len(map_df):,}개"
)

# --------------------------------------------------
# 11. 블루오션 / 레드오션 분석
# --------------------------------------------------

st.markdown("---")

st.markdown(
    '<div class="section-title">🔍 업종별 블루오션 / 레드오션 분석</div>',
    unsafe_allow_html=True
)

st.write(
    "관심 있는 업종을 입력하면 해당 업종의 경쟁 업체 수와 "
    "다른 업종의 경쟁 강도를 비교합니다."
)

selected_business = st.selectbox(
    "분석할 업종을 선택하세요.",
    sorted(df["업종"].unique().tolist())
)

if st.button("🚀 상권 경쟁 분석하기", use_container_width=True):

    business_count = int(
        category_counts.get(selected_business, 0)
    )

    # 업종별 점포 수 분포를 이용한 상대적 경쟁 수준
    q25 = float(category_counts.quantile(0.25))
    q75 = float(category_counts.quantile(0.75))

    if category_count < 2:
        status = "판정 보류"
        color = "gray"
        description = "비교할 다른 업종 데이터가 부족합니다."

    elif business_count <= q25:
        status = "블루오션"
        color = "green"
        description = (
            "다른 업종에 비해 경쟁 업체 수가 적은 편입니다. "
            "잠재적인 시장 기회를 추가로 조사해 볼 만합니다."
        )

    elif business_count >= q75:
        status = "레드오션"
        color = "red"
        description = (
            "다른 업종에 비해 경쟁 업체 수가 많은 편입니다. "
            "차별화 전략과 입지 선정이 중요합니다."
        )

    else:
        status = "보통"
        color = "orange"
        description = (
            "경쟁 업체 수가 중간 수준입니다. "
            "소비자 수요와 경쟁 업체의 특성을 더 분석해 보세요."
        )

    # 전체 점포 중 해당 업종 비율
    percentage = business_count / total_count * 100

    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    st.subheader(f"📌 {selected_business} 분석 결과")

    st.markdown(
        f"<h1 style='color:{color}; font-size:36px;'>"
        f"{status}</h1>",
        unsafe_allow_html=True
    )

    st.write(description)

    a, b, c = st.columns(3)

    with a:
        st.metric("경쟁 업체 수", f"{business_count:,}개")

    with b:
        st.metric("전체 점포 중 비율", f"{percentage:.1f}%")

    with c:
        st.metric("비교 업종 수", f"{category_count:,}개")

    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        f"판정 기준: 업종별 점포 수의 25% 분위수({q25:.1f}개), "
        f"75% 분위수({q75:.1f}개)를 이용한 상대적 분류"
    )

# --------------------------------------------------
# 12. 업종별 통계 그래프
# --------------------------------------------------

st.markdown("---")

st.markdown(
    '<div class="section-title">📈 업종별 점포 수 분석</div>',
    unsafe_allow_html=True
)

top_n = st.slider(
    "표시할 업종 개수",
    min_value=5,
    max_value=min(30, category_count),
    value=min(10, category_count)
)

chart_data = category_counts.head(top_n).sort_values()

st.bar_chart(
    chart_data,
    horizontal=True,
    color="#4B83E6"
)

# --------------------------------------------------
# 13. 원본 데이터 확인
# --------------------------------------------------

with st.expander("📋 업로드한 원본 데이터 확인하기"):

    st.write(f"총 {len(df):,}개의 점포 데이터")

    st.dataframe(
        df[["상호명", "업종", "위도", "경도"]],
        use_container_width=True,
        hide_index=True
    )

    csv_data = df.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        "분석 데이터 CSV 다운로드",
        data=csv_data,
        file_name="상권분석_데이터.csv",
        mime="text/csv"
    )

# --------------------------------------------------
# 14. 하단 안내
# --------------------------------------------------

st.markdown("---")

st.caption(
    "DATA-DRIVEN COMMERCIAL ANALYSIS | "
    "본 분석은 업로드된 공공데이터를 기반으로 한 "
    "상대적 경쟁 밀집도 분석이며 실제 수익성을 보장하지 않습니다."
)
