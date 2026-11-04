
import streamlit as st
import pandas as pd
import folium
import html
import io

from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# ==========================================
# 1. 기본 설정
# ==========================================

st.set_page_config(
    page_title="우리 학교 주변 상권 분석",
    page_icon="📍",
    layout="wide"
)

st.title("📍 우리 학교 주변 상권 분석")
st.caption("DATA-DRIVEN COMMERCIAL LOCATION ANALYSIS")

st.divider()

# ==========================================
# 2. CSV 업로드
# ==========================================

st.sidebar.header("⚙️ 데이터 설정")

uploaded_file = st.sidebar.file_uploader(
    "공공데이터 CSV 업로드",
    type=["csv"]
)

if uploaded_file is None:
    st.title("상권 데이터를 업로드해 주세요!")
    st.info("왼쪽 메뉴에서 공공데이터 CSV 파일을 업로드하세요.")
    st.markdown("""
    ### 필요한 데이터
    - 상호명
    - 상권업종소분류명
    - 위도
    - 경도
    """)
    st.stop()


# ==========================================
# 3. 데이터 불러오기
# ==========================================

@st.cache_data(show_spinner="CSV 데이터를 불러오는 중...")
def load_data(file_bytes):

    errors = []

    for encoding in ["utf-8-sig", "cp949", "euc-kr"]:

        try:
            data = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                low_memory=False
            )
            return data

        except UnicodeDecodeError as e:
            errors.append(str(e))

    raise ValueError("CSV 인코딩을 확인할 수 없습니다.")


try:
    raw_df = load_data(uploaded_file.getvalue())

except Exception as e:
    st.error(f"데이터를 읽을 수 없습니다: {e}")
    st.stop()


# ==========================================
# 4. 컬럼 자동 인식
# ==========================================

def find_col(columns, candidates):

    for candidate in candidates:
        for col in columns:
            if str(col).strip() == candidate:
                return col

    return None


name_col = find_col(
    raw_df.columns,
    ["상호명", "사업장명", "업소명", "점포명"]
)

category_col = find_col(
    raw_df.columns,
    ["상권업종소분류명", "업종소분류명", "업종명"]
)

lat_col = find_col(
    raw_df.columns,
    ["위도", "LAT", "latitude"]
)

lon_col = find_col(
    raw_df.columns,
    ["경도", "LON", "longitude"]
)

missing = []

if name_col is None:
    missing.append("상호명")

if category_col is None:
    missing.append("상권업종소분류명")

if lat_col is None:
    missing.append("위도")

if lon_col is None:
    missing.append("경도")

if missing:
    st.error("필요한 컬럼이 없습니다: " + ", ".join(missing))
    st.write("현재 CSV 컬럼 목록:", list(raw_df.columns))
    st.stop()


# ==========================================
# 5. 데이터 전처리
# ==========================================

df = pd.DataFrame()

df["상호명"] = raw_df[name_col].fillna("이름 없음").astype(str)
df["업종"] = raw_df[category_col].fillna("미분류").astype(str)

df["위도"] = pd.to_numeric(raw_df[lat_col], errors="coerce")
df["경도"] = pd.to_numeric(raw_df[lon_col], errors="coerce")

df = df.dropna(subset=["위도", "경도"])

df = df[
    df["위도"].between(-90, 90)
    & df["경도"].between(-180, 180)
].copy()

df = df.reset_index(drop=True)

if len(df) == 0:
    st.error("유효한 위치 데이터가 없습니다.")
    st.stop()

# ==========================================
# 6. 상권 통계
# ==========================================

category_counts = df["업종"].value_counts()

total_count = len(df)
total_categories = len(category_counts)

top_category = category_counts.index[0]

st.subheader("📊 전체 상권 현황")

col1, col2, col3 = st.columns(3)

col1.metric("전체 점포 수", f"{total_count:,}개")
col2.metric("업종 종류", f"{total_categories:,}개")
col3.metric("최다 업종", top_category)

# ==========================================
# 7. 지도 시각화
# ==========================================

st.divider()
st.subheader("🗺️ 우리 학교 주변 상권 지도")

category_list = ["전체 업종"] + sorted(df["업종"].unique())

selected_category = st.selectbox(
    "지도에 표시할 업종",
    category_list
)

if selected_category == "전체 업종":
    map_df = df
else:
    map_df = df[df["업종"] == selected_category]

st.write(f"지도에 표시할 점포: {len(map_df):,}개")

if len(map_df) == 0:
    st.warning("선택한 업종의 점포가 없습니다.")

else:

    center_lat = float(map_df["위도"].median())
    center_lon = float(map_df["경도"].median())

    map_object = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles="CartoDB positron"
    )

    marker_cluster = MarkerCluster().add_to(map_object)

    # 너무 많은 마커로 인한 화면 지연 방지
    MAX_MARKERS = 5000

    if len(map_df) > MAX_MARKERS:
        st.warning(
            f"점포가 많아 지도에는 최대 {MAX_MARKERS:,}개를 표시합니다. "
            "통계에는 전체 데이터가 반영됩니다."
        )
        display_df = map_df.sample(
            n=MAX_MARKERS,
            random_state=42
        )
    else:
        display_df = map_df

    for row in display_df.itertuples(index=False):

        name = html.escape(str(row.상호명))
        category = html.escape(str(row.업종))

        popup = folium.Popup(
            f"<b>{name}</b><br>업종: {category}",
            max_width=250
        )

        folium.Marker(
            location=[row.위도, row.경도],
            tooltip=name,
            popup=popup
        ).add_to(marker_cluster)

    st_folium(
        map_object,
        use_container_width=True,
        height=550,
        returned_objects=[]
    )

# ==========================================
# 8. 블루오션 / 레드오션 분석
# ==========================================

st.divider()
st.subheader("🔍 블루오션 / 레드오션 분석")

st.write(
    "분석하고 싶은 상권업종소분류명을 직접 입력하세요."
)

business_input = st.text_input(
    "분석할 업종명",
    placeholder="예: 커피전문점, 치킨전문점, 문구용품"
)

if st.button("🚀 경쟁 강도 분석하기", use_container_width=True):

    if not business_input.strip():
        st.warning("분석할 업종명을 입력해 주세요.")

    else:

        # 입력한 업종과 일치하는 점포 찾기
        matched = df[
            df["업종"].str.strip() == business_input.strip()
        ]

        business_count = len(matched)

        if business_count == 0:

            st.warning(
                "해당 업종을 찾을 수 없습니다. "
                "CSV에 등록된 정확한 업종명을 확인해 주세요."
            )

        elif total_categories < 2:

            st.info("비교할 업종이 부족하여 판정할 수 없습니다.")

        else:

            q25 = category_counts.quantile(0.25)
            q75 = category_counts.quantile(0.75)

            percentage = business_count / total_count * 100

            if business_count <= q25:

                result = "🟢 블루오션"
                explanation = (
                    "다른 업종보다 점포 수가 적은 편입니다. "
                    "잠재적인 시장 기회를 추가로 조사해 보세요."
                )

            elif business_count >= q75:

                result = "🔴 레드오션"
                explanation = (
                    "다른 업종보다 점포 수가 많은 편입니다. "
                    "차별화 전략이 중요할 수 있습니다."
                )

            else:

                result = "🟡 보통"
                explanation = (
                    "점포 수가 중간 수준입니다. "
                    "추가적인 시장 분석이 필요합니다."
                )

            st.markdown("### 분석 결과")

            st.subheader(result)

            a, b, c = st.columns(3)

            a.metric("경쟁 점포 수", f"{business_count:,}개")
            b.metric("전체 점포 대비 비율", f"{percentage:.2f}%")
            c.metric("비교 업종 수", f"{total_categories:,}개")

            st.info(explanation)

            st.caption(
                f"상대적 분류 기준: 하위 25% 이하 / "
                f"상위 25% 이상. "
                f"현재 데이터에 포함된 업종별 점포 수 기준입니다."
            )

# ==========================================
# 9. 업종별 통계 그래프
# ==========================================

st.divider()
st.subheader("📈 업종별 점포 수")

top_n = st.slider(
    "표시할 업종 개수",
    min_value=1,
    max_value=min(30, total_categories),
    value=min(10, total_categories)
)

chart_data = category_counts.head(top_n).sort_values()

st.bar_chart(
    chart_data,
    horizontal=True
)

# ==========================================
# 10. 데이터 확인 및 다운로드
# ==========================================

st.divider()

with st.expander("📋 원본 데이터 확인"):

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 분석 데이터 다운로드",
        data=df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ),
        file_name="상권분석.csv",
        mime="text/csv"
    )

st.divider()

st.caption(
    "본 프로그램은 업로드한 공공데이터를 기반으로 "
    "상대적인 업종별 경쟁 밀집도를 분석합니다."
)
