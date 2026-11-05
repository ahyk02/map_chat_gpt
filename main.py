import html
import io

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium


# ==========================================
# 1. 기본 설정
# ==========================================
st.set_page_config(
    page_title="우리 학교 주변 음식점 상권 분석",
    page_icon="🍽️",
    layout="wide",
)

st.title("🍽️ 우리 학교 주변 음식점 상권 분석")
st.caption("음식점 데이터만 필터링해 지도와 업종별 경쟁 밀집도를 분석합니다.")
st.divider()


# ==========================================
# 2. CSV 업로드
# ==========================================
st.sidebar.header("⚙️ 데이터 설정")
uploaded_file = st.sidebar.file_uploader(
    "공공데이터 CSV 업로드",
    type=["csv"],
    help="상권업종대분류명, 상호명, 상권업종소분류명, 위도, 경도 열이 포함된 파일을 사용하세요.",
)

if uploaded_file is None:
    st.info("왼쪽 메뉴에서 상권 데이터 CSV 파일을 업로드해 주세요.")
    st.markdown(
        """
        **필요한 열**
        - `상권업종대분류명` (음식점만 구분하는 데 사용)
        - `상호명`
        - `상권업종소분류명`
        - `위도`, `경도`
        """
    )
    st.stop()


# ==========================================
# 3. CSV 읽기
# ==========================================
@st.cache_data(show_spinner="CSV 데이터를 불러오는 중...")
def load_data(file_bytes: bytes) -> pd.DataFrame:
    last_error = None
    # 공공데이터 CSV에서 자주 사용하는 인코딩 순서
    for encoding in ("cp949", "utf-8-sig", "euc-kr", "utf-8"):
        try:
            data = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                low_memory=False,
            )
            data.columns = [str(col).strip() for col in data.columns]
            return data
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"CSV 인코딩을 확인할 수 없습니다: {last_error}")


try:
    raw_df = load_data(uploaded_file.getvalue())
except Exception as exc:
    st.error(f"CSV 파일을 읽지 못했습니다: {exc}")
    st.stop()


# ==========================================
# 4. 필요한 열 확인
# ==========================================
def find_col(columns, candidates):
    normalized = {str(col).strip(): col for col in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


name_col = find_col(raw_df.columns, ["상호명", "사업장명", "업소명", "점포명"])
major_category_col = find_col(
    raw_df.columns,
    ["상권업종대분류명", "업종대분류명", "업종대분류"],
)
category_col = find_col(
    raw_df.columns,
    ["상권업종소분류명", "업종소분류명", "업종명"],
)
