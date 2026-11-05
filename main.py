        safe_category = html.escape(str(row.업종))
        popup = folium.Popup(
            f"<b>{safe_name}</b><br>음식점 업종: {safe_category}",
            max_width=260,
        )

        # 이미지 아이콘 대신 원형 마커를 사용해 외부 아이콘 로딩 문제 방지
        folium.CircleMarker(
            location=[row.위도, row.경도],
            radius=4,
            color="#e4572e",
            weight=1,
            fill=True,
            fill_color="#f4a261",
            fill_opacity=0.8,
            tooltip=safe_name,
            popup=popup,
        ).add_to(marker_cluster)

    st_folium(
        map_object,
        use_container_width=True,
        height=560,
        returned_objects=[],
    )


# ==========================================
# 8. 블루오션 / 레드오션 분석
# ==========================================
st.divider()
st.subheader("🔍 음식점 업종별 블루오션 / 레드오션 분석")
st.write(
    "분석할 음식점 세부 업종을 선택하면, 이 CSV에 있는 다른 음식점 업종들과 "
    "점포 수를 비교합니다."
)

business_options = sorted(df["업종"].dropna().unique().tolist())
selected_business = st.selectbox(
    "분석할 음식점 업종",
    business_options,
    key="analysis_business",
)

if st.button("🚀 경쟁 강도 분석하기", use_container_width=True):
    business_count = int(category_counts.get(selected_business, 0))
    q25 = float(category_counts.quantile(0.25))
    q75 = float(category_counts.quantile(0.75))
    percentage = business_count / total_count * 100

    if business_count <= q25:
        result = "🟢 상대적으로 점포 수가 적음"
        explanation = (
            "다른 음식점 세부 업종에 비해 점포 수가 적은 편입니다. "
            "실제 창업 가능성을 판단하려면 유동인구, 임대료, 수요 등도 함께 살펴보세요."
        )
    elif business_count >= q75:
        result = "🔴 상대적으로 점포 수가 많음"
        explanation = (
            "다른 음식점 세부 업종에 비해 점포 수가 많은 편입니다. "
            "입지와 차별화 요소를 추가로 조사하는 것이 좋습니다."
        )
    else:
        result = "🟡 중간 수준"
        explanation = (
            "음식점 세부 업종 중 점포 수가 중간 수준입니다. "
            "주변 수요와 경쟁 점포의 위치를 함께 살펴보세요."
        )

    st.markdown("### 분석 결과")
    st.subheader(result)
    a, b, c = st.columns(3)
    a.metric("해당 업종 점포 수", f"{business_count:,}개")
    b.metric("전체 음식점 대비 비율", f"{percentage:.2f}%")
    c.metric("비교한 음식점 세부 업종", f"{total_categories:,}개")
    st.info(explanation)
    st.caption(
        f"분류 기준: 음식점 세부 업종별 점포 수의 하위 25% 이하 / 상위 25% 이상. "
        "이는 업종 간 점포 수를 비교한 상대적 분류이며, 실제 수익성이나 창업 성공 가능성을 뜻하지 않습니다."
    )


# ==========================================
# 9. 음식점 세부 업종별 통계
# ==========================================
st.divider()
st.subheader("📈 음식점 세부 업종별 점포 수")

top_n = st.slider(
    "그래프에 표시할 업종 개수",
    min_value=1,
    max_value=min(30, total_categories),
    value=min(10, total_categories),
)
chart_data = category_counts.head(top_n).sort_values()
st.bar_chart(chart_data, horizontal=True)


# ==========================================
# 10. 필터링된 음식점 데이터 확인 및 다운로드
# ==========================================
st.divider()
with st.expander("📋 분석에 사용된 음식점 데이터 확인"):
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 음식점 분석 데이터 다운로드",
        data=df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="음식점_상권분석.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "분석 기준: 업로드한 CSV의 상권업종대분류명이 '음식'인 점포. "
    "지도에는 최대 5,000개가 표시되며 통계는 유효한 음식점 전체 데이터를 사용합니다."
)
