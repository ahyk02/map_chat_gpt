st.sidebar.subheader("🔎 분석 조건")
all_categories = sorted(food_df["_category"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "음식점 업종", all_categories, default=all_categories,
    help="선택한 업종만 지도와 통계에 표시합니다."
)
search_name = st.sidebar.text_input("음식점 이름 검색", placeholder="예: 김밥, 치킨")

# 학교 좌표는 사용자가 직접 입력할 수 있도록 함. 미입력 시 데이터 중심으로 표시.
st.sidebar.subheader("🏫 학교 위치 (선택)")
center_lat = st.sidebar.number_input("학교 위도", min_value=0.0, max_value=90.0, value=0.0, format="%.6f", help="학교 위도를 입력하면 학교 주변 반경 분석을 할 수 있습니다. 모르면 0으로 두세요.")
center_lon = st.sidebar.number_input("학교 경도", min_value=0.0, max_value=180.0, value=0.0, format="%.6f", help="학교 경도를 입력하면 학교 주변 반경 분석을 할 수 있습니다. 모르면 0으로 두세요.")
use_school_center = center_lat > 0 and center_lon > 0
radius_km = st.sidebar.slider("학교 주변 분석 반경 (km)", 0.5, 5.0, 1.0, 0.5, disabled=not use_school_center)

filtered = food_df[food_df["_category"].isin(selected_categories)].copy()
if search_name.strip():
    filtered = filtered[filtered["_name"].str.contains(search_name.strip(), case=False, na=False)]
if use_school_center:
    filtered["_distance"] = filtered.apply(
        lambda r: haversine_km(center_lat, center_lon, r["_lat"], r["_lon"]), axis=1
    )
    filtered = filtered[filtered["_distance"] <= radius_km]

if filtered.empty:
    st.warning("선택한 조건에 해당하는 음식점이 없습니다. 업종이나 검색어, 분석 반경을 바꿔보세요.")
    st.stop()

# ---------------------------
# 핵심 지표
# ---------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("음식점 수", f"{len(filtered):,}곳")
col2.metric("분석 업종 수", f"{filtered['_category'].nunique():,}개")
col3.metric("표시 지역", "학교 주변" if use_school_center else "전체 데이터")
col4.metric("분석 반경", f"{radius_km:.1f} km" if use_school_center else "미설정")

st.divider()

# ---------------------------
# 지도
# ---------------------------
st.subheader("📍 음식점 위치 지도")
if use_school_center:
    map_center = [center_lat, center_lon]
    zoom = 15
else:
    map_center = [float(filtered["_lat"].mean()), float(filtered["_lon"].mean())]
    zoom = 13

m = folium.Map(location=map_center, zoom_start=zoom, tiles="OpenStreetMap", control_scale=True)
Fullscreen(position="topleft").add_to(m)
if use_school_center:
    folium.Marker(
        [center_lat, center_lon], tooltip="학교 위치",
        popup="<b>학교 위치</b>",
        icon=folium.Icon(color="red", icon="graduation-cap", prefix="fa")
    ).add_to(m)
    folium.Circle(
        [center_lat, center_lon], radius=radius_km * 1000,
        color="#3978d4", weight=2, fill=True, fill_color="#3978d4", fill_opacity=0.08,
        tooltip=f"학교 주변 {radius_km:.1f}km"
    ).add_to(m)

cluster = MarkerCluster(name="음식점")
# 너무 많은 마커로 인한 브라우저 멈춤 방지
MAX_MARKERS = 5000
map_rows = filtered.head(MAX_MARKERS)
for row in map_rows.itertuples(index=False):
    # itertuples는 내부 열 이름이 변할 수 있어 원본 인덱스로 안전하게 접근
    pass
for idx, row in map_rows.iterrows():
    safe_name = html.escape(str(row["_name"]))
    safe_category = html.escape(str(row["_category"]))
    safe_address = html.escape(str(row["_address"]))
    popup_html = (
        f"<div style='width:220px'><b>{safe_name}</b><br>업종: {safe_category}"
        f"<br>주소: {safe_address}</div>"
    )
    folium.Marker(
        [float(row["_lat"]), float(row["_lon"])],
        tooltip=f"{safe_name} · {safe_category}",
        popup=folium.Popup(popup_html, max_width=280),
        icon=folium.Icon(color="blue", icon="cutlery", prefix="fa"),
    ).add_to(cluster)
cluster.add_to(m)
folium.LayerControl().add_to(m)

if len(filtered) > MAX_MARKERS:
    st.info(f"음식점이 많아 지도에는 처음 {MAX_MARKERS:,}곳만 표시합니다. 통계는 전체 {len(filtered):,}곳을 기준으로 계산합니다.")
st_folium(m, height=600, use_container_width=True, returned_objects=[])

# ---------------------------
# 업종 분석
# ---------------------------
st.divider()
st.subheader("📊 업종별 경쟁 밀집도 분석")
left, right = st.columns([1, 1])
counts = filtered["_category"].value_counts().rename_axis("업종").reset_index(name="음식점 수")
with left:
    st.markdown("**업종별 음식점 수**")
    st.bar_chart(counts.set_index("업종"), height=350)
with right:
    st.markdown("**업종별 비율**")
    share = counts.copy()
    share["비율(%)"] = (share["음식점 수"] / share["음식점 수"].sum() * 100).round(1)
    st.dataframe(share, use_container_width=True, hide_index=True, height=350)

# ---------------------------
# 상세 목록 및 다운로드
# ---------------------------
st.divider()
st.subheader("🏪 음식점 목록")
show_cols = ["_name", "_category", "_address", "_lat", "_lon"]
list_df = filtered[show_cols].rename(columns={
    "_name": "상호명", "_category": "업종", "_address": "주소",
    "_lat": "위도", "_lon": "경도"
})
st.dataframe(list_df, use_container_width=True, hide_index=True, height=400)
csv_data = list_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "⬇️ 현재 분석 결과 CSV 다운로드", data=csv_data,
    file_name="음식점_상권분석_결과.csv", mime="text/csv"
)

st.caption("※ 학교 위치를 입력하지 않으면 지도는 필터링된 음식점 데이터의 중심을 기준으로 표시됩니다. 학교 위도·경도는 지도 앱에서 확인해 입력할 수 있습니다.")
