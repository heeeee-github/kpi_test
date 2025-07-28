import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="거래 대시보드", layout="wide")


# 데이터 로드 및 전처리 함수
@st.cache_data
def load_and_process_data():
    df = pd.read_csv("거래데이터_sample.csv", encoding="cp949")
    # 날짜 컬럼 처리
    df["확정일자"] = pd.to_datetime(df["확정일자"], errors="coerce")
    df["판매자가입일"] = pd.to_datetime(df["판매자가입일자"], errors="coerce")
    df["구매자가입일"] = pd.to_datetime(df["구매자가입일자"], errors="coerce")
    # 거래유형 보정
    df["거래유형보정"] = df["거래유형"].map(
        {
            1: "1유형",
            2: "3유형",
            3: "2유형",
            4: "4유형",
            5: "4유형",
            "": "2유형",
            9: "2유형",
            None: "2유형",
        }
    )

    # 거래방식 보정
    df["거래방식보정"] = df["거래방식"].map(
        {
            "정가거래": "정가거래",
            "간편거래": "정가거래",
            "입찰거래": "입찰거래",
            "발주거래": "발주거래",
            "기획전": "기획전",
            "특화상품": "특화상품",
        }
    )

    # 판매자세부구분
    def 분류함수(row):
        if (
            row["구분"] == "청과"
            and row["판매자구분"] == "위탁판매자"
            and pd.notnull(row["판매자"])
            and ("농협" in row["판매자"] or "농업협동" in row["판매자"])
        ):
            return "농협"
        elif row["구분"] == "청과" and row["판매자구분"] == "위탁판매자":
            return "도매법인"
        elif row["구분"] == "청과" and row["판매자구분"] == "직접판매자":
            return "직접판매자"
        elif (
            row["구분"] == "양곡"
            and row["판매자구분"] == "위탁판매자"
            and pd.notnull(row["판매자"])
            and ("농협" in row["판매자"] or "농업협동" in row["판매자"])
        ):
            return "농협"
        elif row["구분"] == "양곡" and row["판매자구분"] == "위탁판매자":
            return "도매법인"
        elif row["구분"] == "양곡" and row["판매자구분"] == "직접판매자":
            return "직접판매자"
        elif (
            row["구분"] == "수산"
            and row["판매자구분"] == "위탁판매자"
            and pd.notnull(row["판매자"])
            and ("수협" in row["판매자"] or "수업협동" in row["판매자"])
        ):
            return "수협"
        elif row["구분"] == "수산" and row["판매자구분"] == "위탁판매자":
            return "도매법인"
        elif row["구분"] == "수산" and row["판매자구분"] == "매수판매자":
            return "매수판매자"
        elif row["구분"] == "수산" and row["판매자구분"] == "직접판매자":
            return "직접판매자"

        elif row["구분"] == "축산" and "돈육" in row["품목"]:
            return "돼지고기"
        elif row["구분"] == "축산" and "한우" in row["품목"]:
            return "소고기"
        elif row["구분"] == "축산" and "닭" in row["품목"]:
            return "닭고기"
        elif row["구분"] == "축산" and "조란" in row["품목"]:
            return "계란"
        elif row["구분"] == "축산" and "알" in row["품목"]:
            return "축산가공"
        else:
            return row["판매자구분"]

    df["판매자세부구분"] = df.apply(분류함수, axis=1)
    # 수치형 컬럼 처리
    numeric_columns = [
        "주문수량",
        "주문물량",
        "주문단가(원)",
        "주문금액(원)",
        "구매확정수량",
        "구매확정물량",
        "구매확정단가(원)",
        "구매확정금액(원)",
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 결측값 처리
    df = df.dropna(subset=["확정일자", "구매확정금액(원)"])
    return df


# 날짜, 필터 컬럼 추가
def add_date_columns(df):
    df = df.copy()
    df["year"] = df["확정일자"].dt.year
    df["year_quarter"] = (
        df["year"].astype(str) + "-Q" + df["확정일자"].dt.quarter.astype(str)
    )
    df["year_month"] = df["확정일자"].dt.strftime("%Y-%m")
    df["year_week"] = df["확정일자"].dt.strftime(
        "%Y-%V"
    )  # ISO 주차 표기법 사용(%Y-%V): 월~일 기준 (1주는 월요일부터 시작)
    return df


# 사이드바 필터
def create_sidebar_filters(df):
    st.sidebar.header(" 필터 설정")
    # 기준선택 (add_date_columns에서 생성한 컬럼 포함)
    date_columns = ["year", "year_quarter", "year_month", "year_week"]
    기준선택 = st.sidebar.selectbox("기준선택", date_columns, key="기준선택")
    # 조회기간 - 데이터의 실제 확정일자 범위 내에서만 선택 가능
    min_date = df["확정일자"].min().date()
    max_date = df["확정일자"].max().date()
    date_range = st.sidebar.date_input(
        " 조회 기간",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # 구분
    구분_options = ["전체"] + list(df["구분"].dropna().unique())
    selected_구분 = st.sidebar.selectbox(" 구분", 구분_options)
    # 벼,찰벼 품목 제외
    exclude_rice = st.sidebar.checkbox("벼,찰벼 품목 제외", value=False)
    # 부류
    부류_options = ["전체"] + list(df["부류"].dropna().unique())
    selected_부류 = st.sidebar.selectbox(" 부류", 부류_options)
    # 품목
    품목_options = ["전체"] + list(df["품목"].dropna().unique())
    selected_품목 = st.sidebar.selectbox(" 품목", 품목_options)
    # 판매자 구분
    seller_type_options = ["전체"] + list(df["판매자구분"].dropna().unique())
    selected_seller_type = st.sidebar.selectbox(" 판매자 구분", seller_type_options)
    # 판매자 세부구분
    seller_dtl_type_options = ["전체"] + list(df["판매자세부구분"].dropna().unique())
    selected_seller_dtl_type = st.sidebar.selectbox(
        " 판매자 세부 구분", seller_dtl_type_options
    )
    # 구매자 구분
    buyer_type_options = ["전체"] + list(df["구매자구분"].dropna().unique())
    selected_buyer_type = st.sidebar.selectbox(" 구매자 구분", buyer_type_options)
    # 거래유형 보정
    trade_type_options = ["전체"] + list(df["거래유형보정"].dropna().unique())
    selected_trade_type = st.sidebar.selectbox(" 거래유형 보정", trade_type_options)
    st.sidebar.markdown("---")
    all_products = st.sidebar.checkbox("품목 전체 보기", value=False)
    if all_products:
        top_n = None
    else:
        top_n = st.sidebar.number_input(
            "품목별 거래흐름 상위 N개", min_value=1, max_value=100, value=20, step=1
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**표 표시 옵션**")
    show_row_total = st.sidebar.checkbox("행합계 표시", value=True)
    show_col_total = st.sidebar.checkbox("열합계 표시", value=True)

    return (
        기준선택,
        date_range,
        selected_구분,
        exclude_rice,
        selected_부류,
        selected_품목,
        selected_seller_type,
        selected_seller_dtl_type,
        selected_buyer_type,
        selected_trade_type,
        top_n,
        show_row_total,
        show_col_total,
    )


# 데이터 필터링
def filter_data(
    df,
    date_range,
    구분,
    exclude_rice,
    부류,
    품목,
    seller_type,
    seller_dtl_type,
    buyer_type,
    trade_type,
):
    filtered_df = df.copy()
    # 날짜 필터
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df["확정일자"].dt.date >= start_date)
            & (filtered_df["확정일자"].dt.date <= end_date)
        ]
    # 구분
    if 구분 != "전체":
        filtered_df = filtered_df[filtered_df["구분"] == 구분]
    # 벼,찰벼 품목 제외
    if exclude_rice:
        filtered_df = filtered_df[~filtered_df["품목"].isin(["벼", "찰벼"])]
    # 부류
    if 부류 != "전체":
        filtered_df = filtered_df[filtered_df["부류"] == 부류]
    # 품목
    if 품목 != "전체":
        filtered_df = filtered_df[filtered_df["품목"] == 품목]
    # 판매자 구분
    if seller_type != "전체":
        filtered_df = filtered_df[filtered_df["판매자구분"] == seller_type]
    # 판매자 세부구분
    if seller_dtl_type != "전체":
        filtered_df = filtered_df[filtered_df["판매자세부구분"] == seller_dtl_type]
    # 구매자 구분
    if buyer_type != "전체":
        filtered_df = filtered_df[filtered_df["구매자구분"] == buyer_type]
    # 거래유형 보정
    if trade_type != "전체":
        filtered_df = filtered_df[filtered_df["거래유형보정"] == trade_type]
    return filtered_df


# KPI 표시 함수
def display_kpi_section(df, title="주요 KPI", period_text="출범 이후"):
    st.markdown(
        f"<h2 style='margin-bottom:0'>{title} <span style='font-size:16px;color:#888'>({period_text})</span></h2>",
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    # KPI 계산
    total_sales = df["구매확정금액(원)"].sum() / 1_000_000
    total_orders = len(df)
    unique_products = df["품목"].nunique()
    unique_sellers = df["판매자"].nunique() if "판매자" in df.columns else 0
    unique_buyers = df["구매자"].nunique() if "구매자" in df.columns else 0
    # 증감률 예시(전년대비, 실제 데이터에 맞게 수정 필요)
    #     <div style='font-size:15px;color:#ff6b6b'>▼{abs(sales_change)}% <span style='color:#eee'>vs. 2019</span></div>
    # sales_change = -2.8
    # profit = total_sales * 0.13  # 임의 예시
    # profit_change = 24.4
    # orders_change = 7.1
    # customers_change = -3.7

    # KPI 카드 스타일
    with col1:
        st.markdown(
            f"""
        <div style='background:#6a5acd;padding:18px 20px 10px 20px;border-radius:12px;color:white;box-shadow:0 2px 8px #eee'>
        <div style='font-size:18px'>거래</div>
        <div style='font-size:30px;font-weight:bold;margin:4px 0'> {total_sales:,.0f}백만원</div>
        <div style='font-size:15px;font-weight:bold;margin:4px 0'>  </div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div style='background:#f7b731;padding:18px 20px 10px 20px;border-radius:12px;color:white;box-shadow:0 2px 8px #eee'>
        <div style='font-size:18px'>구매확정 건 수</div>
        <div style='font-size:30px;font-weight:bold;margin:4px 0'>{total_orders:,} 건</div>
        <div style='font-size:15px;font-weight:bold;margin:4px 0'>  </div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div style='background:#00b894;padding:18px 20px 10px 20px;border-radius:12px;color:white;box-shadow:0 2px 8px #eee'>
        <div style='font-size:18px'>판/구매회원</div>
        <div style='font-size:30px;font-weight:bold;margin:4px 0'>{unique_sellers+unique_buyers:,} 개소</div>
        <div style='font-size:15px;font-weight:bold;margin:4px 0'>판매자 {unique_sellers:,}, 구매자 {unique_buyers:,} 개소</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
        <div style='background:#636e72;padding:18px 20px 10px 20px;border-radius:12px;color:white;box-shadow:0 2px 8px #eee'>
        <div style='font-size:18px'>상품</div>
        <div style='font-size:30px;font-weight:bold;margin:4px 0'>{unique_products:,}개 품목</div>
        <div style='font-size:15px;font-weight:bold;margin:4px 0'> * 품목 보정 필요 </div>
        </div>""",
            unsafe_allow_html=True,
        )


def display_kpi_period_section(df, title="주요 KPI", period_text="조회 기간"):
    st.markdown(f"### {title} ({period_text})")
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col1:
        total_sales = df["구매확정금액(원)"].sum() / 1_000_000
        st.metric(" 총 매출액", f"{total_sales:,.0f}백만원")
    # 누적 거래금액, 일평균, 연말예상
    if not df.empty:
        min_date = df["확정일자"].min()
        max_date = df["확정일자"].max()
        days = (max_date - min_date).days + 1
        total_amt = df["구매확정금액(원)"].sum()
        daily_avg = total_amt / days if days > 0 else 0
        # 올해 12월31일까지 남은 일수
        year = max_date.year
        from datetime import datetime

        end_of_year = datetime(year, 12, 31)
        days_left = (end_of_year - max_date).days
        days_left = max(days_left, 0)  # 음수 방지
        expected_amt = total_amt + (daily_avg * days_left)
        with col2:
            st.metric("일평균 거래금액", f"{daily_avg/1_000_000:,.0f}백만원")
        with col3:
            st.metric(
                f"연말(12.31) 예상 거래액", f"{expected_amt/1_000_000:,.0f}백만원"
            )

    with col4:
        total_orders = len(df)
        st.metric(" 총 거래 건수", f"{total_orders:,}건")
    with col5:
        unique_products = df["품목"].nunique()
        st.metric(" 거래 품목 수", f"{unique_products:,} 품목")
    with col6:
        # 최고 매출 품목
        if not df.empty:
            top_product = df.groupby("품목")["구매확정금액(원)"].sum().idxmax()
            st.metric(" 최고 매출 품목", top_product)
        else:
            st.metric(" 최고 매출 품목", "-")
    with col7:
        unique_sellers = df["판매자"].nunique() if "판매자" in df.columns else 0
        unique_buyers = df["구매자"].nunique() if "구매자" in df.columns else 0
        st.metric("회원 수(판매/구매)", f"{unique_sellers:,}/{unique_buyers:,}")


# 거래 분석 섹션
def display_item_analysis(df, top_n=None, show_row_total=True, show_col_total=True):

    st.markdown("## 📊 통계")

    # CSS 스타일 적용 - 탭 글자 크기 키우기
    st.markdown(
        """
    <style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.5rem;
        font-weight: bold;
        color: #000000; /* 색상 변경 */
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 실제 기준선택 값
    기준선택 = (
        st.session_state["기준선택"] if "기준선택" in st.session_state else "year_month"
    )

    # 탭 생성
    (
        tab_거래분석,
        tab_품목분석,
        tab_회원분석,
        tab_상품등록분석,
        tab_유통효율분석,
        tab_거래다양화분석,
    ) = st.tabs(
        [
            "📈 거래",
            "🛒 품목",
            "👥 회원",
            "🛍️ 상품 등록(개발필요)",
            "📦 유통 효율(개발필요)",
            "🔄 거래 다양화",
        ]
    )

    # 거래분석 탭
    with tab_거래분석:
        # 1. 구분별 거래 흐름
        st.markdown("#### 구분별")
        category_order = ["청과", "축산", "양곡", "수산"]
        _display_flow_section(
            df,
            기준선택,
            "구분",
            category_order,
            color_map={
                "청과": "#2ca02c",
                "축산": "#e377c2",
                "양곡": "#ff7f0e",
                "수산": "#1f77b4",
            },
            show_row_total=show_row_total,
            show_col_total=show_col_total,
        )

        # 2. 판매자구분별 거래 흐름
        st.markdown("#### 판매자 구분별")
        seller_order = sorted(df["판매자구분"].dropna().unique())
        _display_flow_section(
            df,
            기준선택,
            "판매자구분",
            seller_order,
            show_row_total=show_row_total,
            show_col_total=show_col_total,
        )

        # 3. 판매자세부구분별 거래 흐름
        st.markdown("#### 판매자 세부구분별")
        seller_detail_order = sorted(df["판매자세부구분"].dropna().unique())
        _display_flow_section(
            df,
            기준선택,
            "판매자세부구분",
            seller_detail_order,
            show_row_total=show_row_total,
            show_col_total=show_col_total,
        )

        # 4. 거래유형보정별 거래 흐름
        st.markdown("#### 거래유형보정별")
        trade_type_order = sorted(df["거래유형보정"].dropna().unique())
        _display_flow_section(
            df,
            기준선택,
            "거래유형보정",
            trade_type_order,
            show_row_total=show_row_total,
            show_col_total=show_col_total,
        )

    # 품목분석 탭
    with tab_품목분석:
        # 5. 품목별 거래 흐름 (상위 N개)
        st.markdown("#### 품목별")
        if top_n is None:
            # 전체 품목을 거래금액 기준 내림차순으로 정렬
            product_values = (
                df.groupby("품목")["구매확정금액(원)"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            product_order = product_values
            _display_flow_section(
                df,
                기준선택,
                "품목",
                product_order,
                show_row_total=show_row_total,
                show_col_total=show_col_total,
            )
        else:
            try:
                n = int(top_n)
            except Exception:
                n = 10
            top_products = (
                df.groupby("품목")["구매확정금액(원)"]
                .sum()
                .sort_values(ascending=False)
                .head(n)
                .index.tolist()
            )
            product_order = top_products
            _display_flow_section(
                df[df["품목"].isin(product_order)],
                기준선택,
                "품목",
                product_order,
                show_row_total=show_row_total,
                show_col_total=show_col_total,
            )

    # 회원분석 탭
    with tab_회원분석:
        # 신규/기존 회원 및 초도/기존 거래 분석
        st.markdown("#### 신규/기존 회원 및 거래 분석")
        _display_member_analysis_section(df, 기준선택)

        # 6. 판매자별 거래 흐름 (상위 N개)
        st.markdown("#### 판매자별")
        if top_n is None:
            # 전체 판매자를 거래금액 기준 내림차순으로 정렬
            seller_values = (
                df.groupby("판매자")["구매확정금액(원)"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            seller_order = seller_values
            _display_flow_section(
                df,
                기준선택,
                "판매자",
                seller_order,
                show_row_total=show_row_total,
                show_col_total=show_col_total,
            )
        else:
            try:
                n = int(top_n)
            except Exception:
                n = 10
            top_sellers = (
                df.groupby("판매자")["구매확정금액(원)"]
                .sum()
                .sort_values(ascending=False)
                .head(n)
                .index.tolist()
            )
            seller_order = top_sellers
            _display_flow_section(
                df[df["판매자"].isin(seller_order)],
                기준선택,
                "판매자",
                seller_order,
                show_row_total=show_row_total,
                show_col_total=show_col_total,
            )

        # 7. 구매자별 거래 흐름 (상위 N개)
        st.markdown("#### 구매자별")
        if top_n is None:
            # 전체 구매자를 거래금액 기준 내림차순으로 정렬
            buyer_values = (
                df.groupby("구매자")["구매확정금액(원)"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            buyer_order = buyer_values
            _display_flow_section(
                df,
                기준선택,
                "구매자",
                buyer_order,
                show_row_total=show_row_total,
                show_col_total=show_col_total,
            )
        else:
            try:
                n = int(top_n)
            except Exception:
                n = 10
            top_buyers = (
                df.groupby("구매자")["구매확정금액(원)"]
                .sum()
                .sort_values(ascending=False)
                .head(n)
                .index.tolist()
            )
            buyer_order = top_buyers
            _display_flow_section(
                df[df["구매자"].isin(buyer_order)],
                기준선택,
                "구매자",
                buyer_order,
                show_row_total=show_row_total,
                show_col_total=show_col_total,
            )

    with tab_거래다양화분석:

        # 거래다양화를 위한 특별한 집계 함수 호출
        _display_diversification_section(df, 기준선택)


# 회원분석 함수
def _display_member_analysis_section(df, 기준선택):
    """회원분석 - 신규/기존 회원 및 초도/기존 거래 분류"""

    if 기준선택 not in df.columns:
        기준선택 = "year_month"

    # 필요한 컬럼 확인
    required_cols = ["확정일자", "판매자가입일", "구매자가입일", "판매자", "구매자"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.warning(
            f"다음 컬럼이 누락되어 회원분석을 수행할 수 없습니다: {missing_cols}"
        )
        return

    # 데이터 전처리
    analysis_df = df.copy()

    # 날짜 컬럼이 datetime이 아닌 경우 변환
    for date_col in ["확정일자", "판매자가입일", "구매자가입일"]:
        if date_col in analysis_df.columns:
            analysis_df[date_col] = pd.to_datetime(
                analysis_df[date_col], errors="coerce"
            )

    # 기준선택에 따른 날짜 그룹핑
    if 기준선택 == "year":
        analysis_df["거래기준기간"] = analysis_df["확정일자"].dt.year
        analysis_df["판매자가입기준기간"] = analysis_df["판매자가입일"].dt.year
        analysis_df["구매자가입기준기간"] = analysis_df["구매자가입일"].dt.year
    elif 기준선택 == "year_quarter":
        analysis_df["거래기준기간"] = (
            analysis_df["확정일자"].dt.year.astype(str)
            + "-Q"
            + analysis_df["확정일자"].dt.quarter.astype(str)
        )
        analysis_df["판매자가입기준기간"] = (
            analysis_df["판매자가입일"].dt.year.astype(str)
            + "-Q"
            + analysis_df["판매자가입일"].dt.quarter.astype(str)
        )
        analysis_df["구매자가입기준기간"] = (
            analysis_df["구매자가입일"].dt.year.astype(str)
            + "-Q"
            + analysis_df["구매자가입일"].dt.quarter.astype(str)
        )
    elif 기준선택 == "year_month":
        analysis_df["거래기준기간"] = analysis_df["확정일자"].dt.strftime("%Y-%m")
        analysis_df["판매자가입기준기간"] = analysis_df["판매자가입일"].dt.strftime(
            "%Y-%m"
        )
        analysis_df["구매자가입기준기간"] = analysis_df["구매자가입일"].dt.strftime(
            "%Y-%m"
        )
    elif 기준선택 == "year_week":
        analysis_df["거래기준기간"] = analysis_df["확정일자"].dt.strftime("%Y-%V")
        analysis_df["판매자가입기준기간"] = analysis_df["판매자가입일"].dt.strftime(
            "%Y-%V"
        )
        analysis_df["구매자가입기준기간"] = analysis_df["구매자가입일"].dt.strftime(
            "%Y-%V"
        )

    # 신규/기존 회원 분류
    analysis_df["판매자회원구분"] = analysis_df.apply(
        lambda row: (
            "신규회원"
            if row["거래기준기간"] == row["판매자가입기준기간"]
            else "기존회원"
        ),
        axis=1,
    )
    analysis_df["구매자회원구분"] = analysis_df.apply(
        lambda row: (
            "신규회원"
            if row["거래기준기간"] == row["구매자가입기준기간"]
            else "기존회원"
        ),
        axis=1,
    )

    # 초도/기존 거래 분류 (각 회원의 첫 거래인지 확인)
    # 판매자의 첫 거래 확인
    seller_first_trade = analysis_df.groupby("판매자")["확정일자"].min().to_dict()
    analysis_df["판매자초도거래여부"] = analysis_df.apply(
        lambda row: (
            "초도거래"
            if row["확정일자"] == seller_first_trade.get(row["판매자"])
            else "기존거래"
        ),
        axis=1,
    )

    # 구매자의 첫 거래 확인
    buyer_first_trade = analysis_df.groupby("구매자")["확정일자"].min().to_dict()
    analysis_df["구매자초도거래여부"] = analysis_df.apply(
        lambda row: (
            "초도거래"
            if row["확정일자"] == buyer_first_trade.get(row["구매자"])
            else "기존거래"
        ),
        axis=1,
    )

    # 탭으로 분석 결과 표시
    tab_seller_analysis, tab_buyer_analysis, tab_combined_analysis = st.tabs(
        ["🏪 판매자", "🛒 구매자 ", "📊 통합 "]
    )

    with tab_seller_analysis:
        st.subheader("판매자 신규/기존 회원 및 초도/기존 거래")

        # 판매자 분석 테이블
        seller_analysis = (
            analysis_df.groupby([기준선택, "판매자회원구분", "판매자초도거래여부"])
            .agg(
                {"구매확정금액(원)": "sum", "구매확정물량": "sum", "판매자": "nunique"}
            )
            .reset_index()
        )

        seller_analysis.columns = [
            기준선택,
            "회원구분",
            "거래구분",
            "거래금액",
            "거래물량",
            "판매자수",
        ]

        # 피벗 테이블로 변환
        seller_pivot_amount = seller_analysis.pivot_table(
            index=기준선택,
            columns=["회원구분", "거래구분"],
            values="거래금액",
            fill_value=0,
        )

        seller_pivot_count = seller_analysis.pivot_table(
            index=기준선택,
            columns=["회원구분", "거래구분"],
            values="판매자수",
            fill_value=0,
        )

        # 표시
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**판매자 거래금액 (백만원)**")
            seller_pivot_amount_display = seller_pivot_amount / 1_000_000
            st.dataframe(
                seller_pivot_amount_display.style.format("{:,.0f}"),
                use_container_width=True,
            )

        with col2:
            st.markdown("**판매자 수**")
            st.dataframe(
                seller_pivot_count.style.format("{:,0f}"), use_container_width=True
            )

    with tab_buyer_analysis:
        st.subheader("구매자 신규/기존 회원 및 초도/기존 거래 분석")

        # 구매자 분석 테이블
        buyer_analysis = (
            analysis_df.groupby([기준선택, "구매자회원구분", "구매자초도거래여부"])
            .agg(
                {"구매확정금액(원)": "sum", "구매확정물량": "sum", "구매자": "nunique"}
            )
            .reset_index()
        )

        buyer_analysis.columns = [
            기준선택,
            "회원구분",
            "거래구분",
            "거래금액",
            "거래물량",
            "구매자수",
        ]

        # 피벗 테이블로 변환
        buyer_pivot_amount = buyer_analysis.pivot_table(
            index=기준선택,
            columns=["회원구분", "거래구분"],
            values="거래금액",
            fill_value=0,
        )

        buyer_pivot_count = buyer_analysis.pivot_table(
            index=기준선택,
            columns=["회원구분", "거래구분"],
            values="구매자수",
            fill_value=0,
        )

        # 표시
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**구매자 거래금액 (백만원)**")
            buyer_pivot_amount_display = buyer_pivot_amount / 1_000_000
            st.dataframe(
                buyer_pivot_amount_display.style.format("{:,.0f}"),
                use_container_width=True,
            )

        with col2:
            st.markdown("**구매자 수**")
            st.dataframe(
                buyer_pivot_count.style.format("{:,0f}"), use_container_width=True
            )

    with tab_combined_analysis:
        st.subheader("통합")

        # 통합 분석 - 신규회원/기존회원 별 초도거래/기존거래 비율
        combined_stats = []

        # 각 기간별 통계
        for period in sorted(analysis_df[기준선택].unique()):
            period_data = analysis_df[analysis_df[기준선택] == period]

            # 판매자 통계
            seller_stats = (
                period_data.groupby(["판매자회원구분", "판매자초도거래여부"])
                .agg({"구매확정금액(원)": "sum", "판매자": "nunique"})
                .reset_index()
            )
            seller_stats["구분"] = "판매자"
            seller_stats = seller_stats.rename(
                columns={
                    "판매자회원구분": "회원구분",
                    "판매자초도거래여부": "거래구분",
                    "판매자": "회원수",
                }
            )

            # 구매자 통계
            buyer_stats = (
                period_data.groupby(["구매자회원구분", "구매자초도거래여부"])
                .agg({"구매확정금액(원)": "sum", "구매자": "nunique"})
                .reset_index()
            )
            buyer_stats["구분"] = "구매자"
            buyer_stats = buyer_stats.rename(
                columns={
                    "구매자회원구분": "회원구분",
                    "구매자초도거래여부": "거래구분",
                    "구매자": "회원수",
                }
            )

            # 기간 정보 추가
            seller_stats[기준선택] = period
            buyer_stats[기준선택] = period

            combined_stats.extend([seller_stats, buyer_stats])

        if combined_stats:
            combined_df = pd.concat(combined_stats, ignore_index=True)

            # 요약 테이블 생성
            summary_table = (
                combined_df.groupby([기준선택, "구분", "회원구분", "거래구분"])
                .agg({"구매확정금액(원)": "sum", "회원수": "sum"})
                .reset_index()
            )

            # 피벗 테이블로 변환
            summary_pivot = summary_table.pivot_table(
                index=[기준선택, "구분"],
                columns=["회원구분", "거래구분"],
                values="구매확정금액(원)",
                fill_value=0,
            )

            st.markdown("**통합 거래금액 분석 (백만원)**")
            summary_pivot_display = summary_pivot / 1_000_000
            st.dataframe(
                summary_pivot_display.style.format("{:,.0f}"),
                use_container_width=True,
                height=400,
            )

            # 비율 분석
            st.markdown("**신규회원 비율 (%)**")

            # 각 기간별 신규회원 비율 계산
            ratio_data = []
            for period in sorted(analysis_df[기준선택].unique()):
                period_data = analysis_df[analysis_df[기준선택] == period]

                # 판매자 신규회원 비율
                seller_total = period_data["판매자"].nunique()
                seller_new = period_data[period_data["판매자회원구분"] == "신규회원"][
                    "판매자"
                ].nunique()
                seller_new_ratio = (
                    (seller_new / seller_total * 100) if seller_total > 0 else 0
                )

                # 구매자 신규회원 비율
                buyer_total = period_data["구매자"].nunique()
                buyer_new = period_data[period_data["구매자회원구분"] == "신규회원"][
                    "구매자"
                ].nunique()
                buyer_new_ratio = (
                    (buyer_new / buyer_total * 100) if buyer_total > 0 else 0
                )

                ratio_data.append(
                    {
                        기준선택: period,
                        "판매자_신규회원_비율(%)": seller_new_ratio,
                        "구매자_신규회원_비율(%)": buyer_new_ratio,
                        "판매자_총수": seller_total,
                        "구매자_총수": buyer_total,
                    }
                )

            ratio_df = pd.DataFrame(ratio_data)
            st.dataframe(
                ratio_df.style.format(
                    {
                        "판매자_신규회원_비율(%)": "{:.1f}%",
                        "구매자_신규회원_비율(%)": "{:.1f}%",
                        "판매자_총수": "{:,}",
                        "구매자_총수": "{:,}",
                    }
                ),
                use_container_width=True,
            )


# 거래다양화 분석을 위한 함수
def _display_diversification_section(df, 기준선택):
    """거래다양화 분석 - 거래방식별 거래건수를 포함한 집계"""

    if 기준선택 not in df.columns:
        기준선택 = "year_month"

    # 거래방식 컬럼 확인
    if "거래방식보정" in df.columns:
        group_col = "거래방식보정"
    elif "거래유형보정" in df.columns:
        group_col = "거래유형보정"
    elif "거래유형" in df.columns:
        group_col = "거래유형"
    else:
        st.warning("거래방식 관련 컬럼을 찾을 수 없습니다.")
        return

    # 구매확정금액, 구매확정물량, 거래건수 모두 집계
    flow = (
        df.groupby([기준선택, group_col])
        .agg(
            {
                "구매확정금액(원)": "sum",
                "구매확정물량": "sum",
                "확정일자": "count",  # 거래건수
            }
        )
        .reset_index()
    )

    # 컬럼명 변경 및 단위 변환
    flow["구매확정금액(백만원)"] = flow["구매확정금액(원)"] / 1_000_000
    flow["구매확정물량(톤)"] = flow["구매확정물량"] / 1_000
    flow["거래건수"] = flow["확정일자"]

    # year_week인 경우 시간순 정렬
    if 기준선택 == "year_week":
        flow = flow.sort_values(기준선택)

    # 거래방식 순서 정렬 (거래금액 기준 내림차순)
    group_totals = (
        flow.groupby(group_col)["구매확정금액(백만원)"]
        .sum()
        .sort_values(ascending=False)
    )
    col_order = group_totals.index.tolist()

    # 카테고리컬 데이터로 변환하여 순서 지정
    flow[group_col] = pd.Categorical(
        flow[group_col], categories=col_order, ordered=True
    )

    # 금액 피벗 테이블
    pivot_amount = (
        flow.pivot(index=기준선택, columns=group_col, values="구매확정금액(백만원)")
        .fillna(0)
        .astype(float)
    )
    pivot_amount = pivot_amount.reindex(columns=col_order)

    # 물량 피벗 테이블
    pivot_volume = (
        flow.pivot(index=기준선택, columns=group_col, values="구매확정물량(톤)")
        .fillna(0)
        .astype(float)
    )
    pivot_volume = pivot_volume.reindex(columns=col_order)

    # 거래건수 피벗 테이블
    pivot_count = (
        flow.pivot(index=기준선택, columns=group_col, values="거래건수")
        .fillna(0)
        .astype(int)
    )
    pivot_count = pivot_count.reindex(columns=col_order)

    # 합계 행 추가
    total_row_amount = pd.DataFrame(pivot_amount.sum(axis=0)).T
    total_row_amount.index = ["합계"]

    total_row_volume = pd.DataFrame(pivot_volume.sum(axis=0)).T
    total_row_volume.index = ["합계"]

    total_row_count = pd.DataFrame(pivot_count.sum(axis=0)).T
    total_row_count.index = ["합계"]

    # 합계 열 추가
    pivot_amount["합계"] = pivot_amount.sum(axis=1)
    pivot_volume["합계"] = pivot_volume.sum(axis=1)
    pivot_count["합계"] = pivot_count.sum(axis=1)

    total_row_amount["합계"] = total_row_amount.sum(axis=1)
    total_row_volume["합계"] = total_row_volume.sum(axis=1)
    total_row_count["합계"] = total_row_count.sum(axis=1)

    # 최종 테이블 생성
    pivot_amount_with_total = pd.concat([pivot_amount, total_row_amount])
    pivot_volume_with_total = pd.concat([pivot_volume, total_row_volume])
    pivot_count_with_total = pd.concat([pivot_count, total_row_count])

    # 컬럼 레이아웃
    col_table1, col_table2, col_table3 = st.columns([1, 1, 1])

    # 탭으로 금액, 물량, 건수 구분하여 표시
    with col_table1:
        tab_amount, tab_volume, tab_count = st.tabs(
            [" 금액(백만원)", " 물량(톤)", " 건수"]
        )

        with tab_amount:
            amount_selection = st.dataframe(
                pivot_amount_with_total.style.format("{:,.0f}"),
                use_container_width=True,
                height=400,
                on_select="rerun",
                selection_mode="single-row",
                key=f"amount_table_trade_type",
            )

        with tab_volume:
            volume_selection = st.dataframe(
                pivot_volume_with_total.style.format("{:,.0f}"),
                use_container_width=True,
                height=400,
                on_select="rerun",
                selection_mode="single-row",
                key=f"volume_table_trade_type",
            )

        with tab_count:
            count_selection = st.dataframe(
                pivot_count_with_total.style.format("{:,.0f}"),
                use_container_width=True,
                height=400,
                on_select="rerun",
                selection_mode="single-row",
                key=f"count_table_trade_type",
            )

    with col_table2:
        # 거래방식별 요약 통계
        st.markdown("**거래방식별 요약 통계**")

        # 전체 기간 합계
        summary_stats = (
            flow.groupby(group_col)
            .agg(
                {
                    "구매확정금액(백만원)": "sum",
                    "구매확정물량(톤)": "sum",
                    "거래건수": "sum",
                }
            )
            .reset_index()
        )

        # 비중 계산
        total_amount = summary_stats["구매확정금액(백만원)"].sum()
        total_volume = summary_stats["구매확정물량(톤)"].sum()
        total_count = summary_stats["거래건수"].sum()

        summary_stats["금액비중(%)"] = (
            summary_stats["구매확정금액(백만원)"] / total_amount * 100
        ).round(1)
        summary_stats["물량비중(%)"] = (
            summary_stats["구매확정물량(톤)"] / total_volume * 100
        ).round(1)
        summary_stats["건수비중(%)"] = (
            summary_stats["거래건수"] / total_count * 100
        ).round(1)

        # 정렬 (거래금액 기준 내림차순)
        summary_stats = summary_stats.sort_values(
            "구매확정금액(백만원)", ascending=False
        )

        st.dataframe(
            summary_stats.style.format(
                {
                    "구매확정금액(백만원)": "{:,.0f}",
                    "구매확정물량(톤)": "{:,.0f}",
                    "거래건수": "{:,}",
                    "금액비중(%)": "{:.1f}%",
                    "물량비중(%)": "{:.1f}%",
                    "건수비중(%)": "{:.1f}%",
                }
            ),
            use_container_width=True,
            hide_index=True,
            height=400,
        )

    with col_table3:
        # 그래프 표시
        st.markdown("**거래방식별 추이**")

        # 그래프 탭
        tab_amount_chart, tab_volume_chart, tab_count_chart = st.tabs(
            [" 금액", " 물량", " 건수"]
        )

        with tab_amount_chart:
            import plotly.express as px

            # X축 순서 설정
            if 기준선택 == "year_week":
                x_order = sorted(flow[기준선택].unique())
                category_orders = {기준선택: x_order}
            else:
                category_orders = None

            fig = px.line(
                flow,
                x=기준선택,
                y="구매확정금액(백만원)",
                color=group_col,
                markers=True,
                title=f"{기준선택}별 거래방식별 거래금액 추이",
                category_orders=category_orders,
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with tab_volume_chart:
            fig = px.line(
                flow,
                x=기준선택,
                y="구매확정물량(톤)",
                color=group_col,
                markers=True,
                title=f"{기준선택}별 거래방식별 거래물량 추이",
                category_orders=category_orders,
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with tab_count_chart:
            fig = px.line(
                flow,
                x=기준선택,
                y="거래건수",
                color=group_col,
                markers=True,
                title=f"{기준선택}별 거래방식별 거래건수 추이",
                category_orders=category_orders,
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # 선택된 셀에 대한 거래내역 표시
    _display_trade_type_transaction_details(
        df,
        기준선택,
        group_col,
        amount_selection,
        volume_selection,
        count_selection,
        pivot_amount_with_total,
        pivot_volume_with_total,
        pivot_count_with_total,
    )


# 거래방식별 선택된 셀의 거래내역을 표시하는 함수
def _display_trade_type_transaction_details(
    df,
    기준선택,
    group_col,
    amount_selection,
    volume_selection,
    count_selection,
    pivot_amount_with_total,
    pivot_volume_with_total,
    pivot_count_with_total,
):
    """선택된 피벗 테이블 행에 해당하는 거래내역을 표시"""

    selected_period = None
    table_type = None

    # 금액 테이블에서 선택된 행 처리
    if (
        amount_selection
        and "selection" in amount_selection
        and "rows" in amount_selection["selection"]
    ):
        if amount_selection["selection"]["rows"]:
            selected_row_idx = amount_selection["selection"]["rows"][0]
            if selected_row_idx < len(pivot_amount_with_total.index):
                selected_period = pivot_amount_with_total.index[selected_row_idx]
                table_type = "금액"

    # 물량 테이블에서 선택된 행 처리
    elif (
        volume_selection
        and "selection" in volume_selection
        and "rows" in volume_selection["selection"]
    ):
        if volume_selection["selection"]["rows"]:
            selected_row_idx = volume_selection["selection"]["rows"][0]
            if selected_row_idx < len(pivot_volume_with_total.index):
                selected_period = pivot_volume_with_total.index[selected_row_idx]
                table_type = "물량"

    # 건수 테이블에서 선택된 행 처리
    elif (
        count_selection
        and "selection" in count_selection
        and "rows" in count_selection["selection"]
    ):
        if count_selection["selection"]["rows"]:
            selected_row_idx = count_selection["selection"]["rows"][0]
            if selected_row_idx < len(pivot_count_with_total.index):
                selected_period = pivot_count_with_total.index[selected_row_idx]
                table_type = "건수"

    # 선택된 기간이 있고 "합계" 행이 아닌 경우
    if selected_period and selected_period != "합계":
        _show_filtered_transactions_by_period(
            df,
            기준선택,
            group_col,
            selected_period,
            table_type,
            pivot_amount_with_total,
        )


# 공통 거래흐름 표/비율/그래프 함수
def _display_flow_section(
    df,
    기준선택,
    group_col,
    col_order,
    color_map=None,
    show_row_total=True,
    show_col_total=True,
):
    # group_col: 피벗의 columns
    # col_order: 컬럼 순서
    # color_map: plotly color map
    if 기준선택 not in df.columns:
        기준선택 = "year_month"

    # 구매확정금액과 구매확정물량 모두 집계
    flow = (
        df.groupby([기준선택, group_col])
        .agg({"구매확정금액(원)": "sum", "구매확정물량": "sum"})
        .reset_index()
    )

    flow["구매확정금액(백만원)"] = flow["구매확정금액(원)"] / 1_000_000
    flow["구매확정물량(톤)"] = flow["구매확정물량"] / 1_000  # kg -> 톤 변환

    # year_week인 경우 시간순 정렬을 위한 처리
    if 기준선택 == "year_week":
        # year_week 문자열을 기준으로 정렬 (YYYY-WW 형태)
        flow = flow.sort_values(기준선택)

    # 거래금액 기준으로 그룹 내림차순 정렬
    if col_order is None or len(col_order) == 0:
        # 입력된 col_order가 없는 경우 거래금액 합계로 내림차순 정렬
        group_totals = (
            flow.groupby(group_col)["구매확정금액(백만원)"]
            .sum()
            .sort_values(ascending=False)
        )
        col_order = group_totals.index.tolist()

    # 카테고리컬 데이터로 변환하여 순서 지정
    flow[group_col] = pd.Categorical(
        flow[group_col], categories=col_order, ordered=True
    )

    # 금액 피벗 테이블
    pivot_amount = (
        flow.pivot(index=기준선택, columns=group_col, values="구매확정금액(백만원)")
        .fillna(0)
        .astype(float)
    )
    # 내림차순 정렬된 col_order를 그대로 사용
    pivot_amount = pivot_amount.reindex(columns=col_order)

    # 물량 피벗 테이블
    pivot_volume = (
        flow.pivot(index=기준선택, columns=group_col, values="구매확정물량(톤)")
        .fillna(0)
        .astype(float)
    )
    # 금액 기준 정렬된 col_order와 동일하게 물량도 정렬
    pivot_volume = pivot_volume.reindex(columns=col_order)

    # 금액 합계 행(행 합계) 추가
    total_row_amount = pd.DataFrame(pivot_amount.sum(axis=0)).T
    total_row_amount.index = ["합계"]

    # 물량 합계 행(행 합계) 추가
    total_row_volume = pd.DataFrame(pivot_volume.sum(axis=0)).T
    total_row_volume.index = ["합계"]

    # group별 합계(열 합계) 추가
    if show_col_total:
        pivot_amount["합계"] = pivot_amount.sum(axis=1)
        pivot_volume["합계"] = pivot_volume.sum(axis=1)
        total_row_amount["합계"] = total_row_amount.sum(axis=1)
        total_row_volume["합계"] = total_row_volume.sum(axis=1)

    # 최종 테이블 생성
    if show_row_total:
        pivot_amount_with_total = pd.concat([pivot_amount, total_row_amount])
        pivot_volume_with_total = pd.concat([pivot_volume, total_row_volume])
    else:
        pivot_amount_with_total = pivot_amount.copy()
        pivot_volume_with_total = pivot_volume.copy()

    # 컬럼 레이아웃
    col_table1, col_table2, col_table3, col_chart = st.columns([1.5, 1.5, 1.5, 1])

    # 탭으로 금액과 물량 구분하여 표시
    with col_table1:
        tab_amount, tab_volume = st.tabs([" 금액(백만원)", " 물량(톤)"])

        with tab_amount:
            amount_selection = st.dataframe(
                pivot_amount_with_total.style.format("{:,.0f}"),
                use_container_width=True,
                height=400,
                on_select="rerun",
                selection_mode="single-row",
                key=f"amount_table_{group_col}",
            )

            st.markdown(
                """
                <div style="background-color: #FFF8DC; padding: 10px; border-radius: 5px; border: 1px solid #DDD;">
                    <strong>💡 팁: 표의 행을 클릭하면 해당 거래내역을 아래에서 확인</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab_volume:

            volume_selection = st.dataframe(
                pivot_volume_with_total.style.format("{:,.0f}"),
                use_container_width=True,
                height=400,
                on_select="rerun",
                selection_mode="single-row",
                key=f"volume_table_{group_col}",
            )
            st.markdown(
                """
                <div style="background-color: #FFF8DC; padding: 10px; border-radius: 5px; border: 1px solid #DDD;">
                    <strong>💡 팁: 표의 행을 클릭하면 해당 거래내역을 아래에서 확인</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with col_table2:
        # 행 비율(%) 계산 (합계 컬럼 제외) - 금액 기준
        pivot_for_pct = pivot_amount_with_total.copy()
        if show_col_total and "합계" in pivot_for_pct.columns:
            pivot_for_pct = pivot_for_pct.drop("합계", axis=1)

        row_sum_amount = pivot_for_pct.sum(axis=1)
        row_pct_amount = pivot_for_pct.div(row_sum_amount, axis=0) * 100

        if show_col_total:
            row_pct_amount["합계"] = 100.0
        row_pct_amount = row_pct_amount.round(1)

        # 탭으로 금액과 물량 비율 구분하여 표시
        tab_amount_pct, tab_volume_pct = st.tabs([" 금액 비율(%)", " 물량 비율(%)"])

        with tab_amount_pct:
            st.dataframe(
                row_pct_amount.style.format("{:.1f}%"),
                use_container_width=True,
                height=400,
            )

        with tab_volume_pct:
            # 물량 비율 계산
            pivot_vol_for_pct = pivot_volume_with_total.copy()
            if show_col_total and "합계" in pivot_vol_for_pct.columns:
                pivot_vol_for_pct = pivot_vol_for_pct.drop("합계", axis=1)

            row_sum_volume = pivot_vol_for_pct.sum(axis=1)
            row_pct_volume = pivot_vol_for_pct.div(row_sum_volume, axis=0) * 100

            if show_col_total:
                row_pct_volume["합계"] = 100.0
            row_pct_volume = row_pct_volume.round(1)

            st.dataframe(
                row_pct_volume.style.format("{:.1f}%"),
                use_container_width=True,
                height=400,
            )
    with col_table3:
        # 이전 기준선택기간 대비 증감률 (합계 컬럼 제외)
        tab_amount_change, tab_volume_change = st.tabs(
            [" 금액 증감률(%)", " 물량 증감률(%)"]
        )

        # 금액 증감률 탭
        with tab_amount_change:
            try:
                # 모든 기간에 대한 데이터 준비
                all_periods = sorted(df[기준선택].unique())

                if (
                    len(all_periods) >= 2
                ):  # 최소 2개 이상의 기간이 있어야 증감률 계산 가능
                    # 원본 피벗 테이블에서 합계 컬럼 제외
                    pivot_cols = (
                        [col for col in pivot_amount.columns if col != "합계"]
                        if show_col_total
                        else list(pivot_amount.columns)
                    )

                    # 증감률 계산을 위한 빈 데이터프레임 생성
                    change_pct_df = pd.DataFrame(
                        index=pivot_amount.index, columns=pivot_cols
                    )

                    # 각 기간별 이전 기간과 비교하여 증감률 계산
                    for i in range(1, len(pivot_amount.index)):
                        current_idx = pivot_amount.index[i]
                        prev_idx = pivot_amount.index[i - 1]

                        # 증감률 계산 (0으로 나누는 오류 방지)
                        for col in pivot_cols:
                            current_val = pivot_amount.loc[current_idx, col]
                            prev_val = pivot_amount.loc[prev_idx, col]

                            if prev_val != 0:
                                pct_change = (current_val - prev_val) / prev_val * 100
                                change_pct_df.loc[current_idx, col] = pct_change
                            else:
                                # 이전 값이 0인 경우 현재 값이 0이면 0%, 아니면 100% 변화
                                change_pct_df.loc[current_idx, col] = (
                                    0.0 if current_val == 0 else 100.0
                                )

                    # 첫 번째 기간은 이전 기간이 없으므로 증감률을 계산할 수 없음
                    change_pct_df.loc[pivot_amount.index[0]] = float("nan")

                    # 합계 행(맨 아래 행) 제외 - 합계 행은 증감률 계산에서 제외
                    if show_row_total and "합계" in change_pct_df.index:
                        change_pct_df = change_pct_df.drop("합계")

                    # 증감률 표시용 최종 데이터프레임 생성
                    # 모든 원본 행과 동일한 형태를 유지하고 합계 열 추가
                    final_change_pct = pd.DataFrame(
                        index=pivot_amount.index, columns=pivot_amount.columns
                    )

                    # 계산된 증감률 데이터 복사
                    for idx in change_pct_df.index:
                        for col in change_pct_df.columns:
                            final_change_pct.loc[idx, col] = change_pct_df.loc[idx, col]

                    # 합계 열에는 행별 평균 증감률 설정 (NaN 제외)
                    if show_col_total:
                        for idx in final_change_pct.index:
                            row_values = (
                                change_pct_df.loc[idx].dropna()
                                if idx in change_pct_df.index
                                else pd.Series()
                            )
                            if not row_values.empty:
                                final_change_pct.loc[idx, "합계"] = row_values.mean()
                            else:
                                final_change_pct.loc[idx, "합계"] = float("nan")

                    # 스타일 적용 및 표시
                    def highlight_pos_neg(val):
                        if pd.isna(val):
                            return "color: gray"
                        elif val > 0:
                            return "color: #2ca02c"  # 양수 값은 녹색
                        elif val < 0:
                            return "color: #d62728"  # 음수 값은 빨간색
                        else:
                            return ""

                    # 스타일 적용
                    styled = final_change_pct.style.format(
                        lambda x: "-" if pd.isna(x) else f"{x:.1f}%"
                    )
                    styled = styled.applymap(highlight_pos_neg)

                    st.dataframe(
                        styled,
                        use_container_width=True,
                        height=400,
                    )
                else:
                    st.info("증감률 계산을 위해서는 2개 이상의 기간이 필요합니다.")
            except Exception as e:
                st.warning(f"금액 증감률 계산 중 오류가 발생했습니다: {str(e)}")
                # 오류 발생 시 빈 데이터프레임 표시
                empty_df = pd.DataFrame(
                    index=pivot_amount_with_total.index,
                    columns=pivot_amount_with_total.columns,
                )
                empty_df = empty_df.fillna("-")
                st.dataframe(
                    empty_df.style.format("{}"),
                    use_container_width=True,
                    height=400,
                )

        # 물량 증감률 탭
        with tab_volume_change:
            try:
                # 모든 기간에 대한 데이터 준비
                all_periods = sorted(df[기준선택].unique())

                if (
                    len(all_periods) >= 2
                ):  # 최소 2개 이상의 기간이 있어야 증감률 계산 가능
                    # 원본 피벗 테이블에서 합계 컬럼 제외
                    pivot_cols = (
                        [col for col in pivot_volume.columns if col != "합계"]
                        if show_col_total
                        else list(pivot_volume.columns)
                    )

                    # 증감률 계산을 위한 빈 데이터프레임 생성
                    change_pct_df = pd.DataFrame(
                        index=pivot_volume.index, columns=pivot_cols
                    )

                    # 각 기간별 이전 기간과 비교하여 증감률 계산
                    for i in range(1, len(pivot_volume.index)):
                        current_idx = pivot_volume.index[i]
                        prev_idx = pivot_volume.index[i - 1]

                        # 증감률 계산 (0으로 나누는 오류 방지)
                        for col in pivot_cols:
                            current_val = pivot_volume.loc[current_idx, col]
                            prev_val = pivot_volume.loc[prev_idx, col]

                            if prev_val != 0:
                                pct_change = (current_val - prev_val) / prev_val * 100
                                change_pct_df.loc[current_idx, col] = pct_change
                            else:
                                # 이전 값이 0인 경우 현재 값이 0이면 0%, 아니면 100% 변화
                                change_pct_df.loc[current_idx, col] = (
                                    0.0 if current_val == 0 else 100.0
                                )

                    # 첫 번째 기간은 이전 기간이 없으므로 증감률을 계산할 수 없음
                    change_pct_df.loc[pivot_volume.index[0]] = float("nan")

                    # 합계 행(맨 아래 행) 제외 - 합계 행은 증감률 계산에서 제외
                    if show_row_total and "합계" in change_pct_df.index:
                        change_pct_df = change_pct_df.drop("합계")

                    # 증감률 표시용 최종 데이터프레임 생성
                    # 모든 원본 행과 동일한 형태를 유지하고 합계 열 추가
                    final_change_pct = pd.DataFrame(
                        index=pivot_volume.index, columns=pivot_volume.columns
                    )

                    # 계산된 증감률 데이터 복사
                    for idx in change_pct_df.index:
                        for col in change_pct_df.columns:
                            final_change_pct.loc[idx, col] = change_pct_df.loc[idx, col]

                    # 합계 열에는 행별 평균 증감률 설정 (NaN 제외)
                    if show_col_total:
                        for idx in final_change_pct.index:
                            row_values = (
                                change_pct_df.loc[idx].dropna()
                                if idx in change_pct_df.index
                                else pd.Series()
                            )
                            if not row_values.empty:
                                final_change_pct.loc[idx, "합계"] = row_values.mean()
                            else:
                                final_change_pct.loc[idx, "합계"] = float("nan")

                    # 스타일 적용 및 표시
                    def highlight_pos_neg(val):
                        if pd.isna(val):
                            return "color: gray"
                        elif val > 0:
                            return "color: #2ca02c"  # 양수 값은 녹색
                        elif val < 0:
                            return "color: #d62728"  # 음수 값은 빨간색
                        else:
                            return ""

                    # 스타일 적용
                    styled = final_change_pct.style.format(
                        lambda x: "-" if pd.isna(x) else f"{x:.1f}%"
                    )
                    styled = styled.applymap(highlight_pos_neg)

                    st.dataframe(
                        styled,
                        use_container_width=True,
                        height=400,
                    )
                else:
                    st.info("증감률 계산을 위해서는 2개 이상의 기간이 필요합니다.")
            except Exception as e:
                st.warning(f"물량 증감률 계산 중 오류가 발생했습니다: {str(e)}")
                # 오류 발생 시 빈 데이터프레임 표시
                empty_df = pd.DataFrame(
                    index=pivot_volume_with_total.index,
                    columns=pivot_volume_with_total.columns,
                )
                empty_df = empty_df.fillna("-")
                st.dataframe(
                    empty_df.style.format("{}"),
                    use_container_width=True,
                    height=400,
                )

    # 그래프 표시
    with col_chart:
        tab_amount_chart, tab_volume_chart = st.tabs([" 금액 그래프", " 물량 그래프"])

        with tab_amount_chart:
            # 그룹별 합계 데이터 생성
            total_by_period = (
                flow.groupby(기준선택)["구매확정금액(백만원)"].sum().reset_index()
            )

            # X축 순서 설정 (year_week인 경우 시간순 정렬)
            if 기준선택 == "year_week":
                x_order = sorted(flow[기준선택].unique())
                category_orders = {기준선택: x_order}
            else:
                category_orders = None

            # 누적 막대그래프 생성
            if color_map is None:
                fig_bar = px.bar(
                    flow,
                    x=기준선택,
                    y="구매확정금액(백만원)",
                    color=group_col,
                    title=f"{기준선택}별 {group_col}별 거래금액 추이 (단위: 백만원)",
                    labels={"구매확정금액(백만원)": "거래금액(백만원)"},
                    category_orders=category_orders,
                )
            else:
                fig_bar = px.bar(
                    flow,
                    x=기준선택,
                    y="구매확정금액(백만원)",
                    color=group_col,
                    title=f"{기준선택}별 {group_col}별 거래금액 추이 (단위: 백만원)",
                    labels={"구매확정금액(백만원)": "거래금액(백만원)"},
                    color_discrete_map=color_map,
                    category_orders=category_orders,
                )

            # 합계 선그래프 추가
            fig_bar.add_scatter(
                x=total_by_period[기준선택],
                y=total_by_period["구매확정금액(백만원)"],
                mode="lines+markers",
                name="합계",
                line=dict(color="red", width=3),
                marker=dict(size=8, color="red"),
                yaxis="y",
            )

            # 레이아웃 업데이트
            fig_bar.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=0.95, xanchor="center", x=0.5
                ),
                title=dict(y=0.95, x=0.5, xanchor="center"),
                margin=dict(t=120, b=50, l=50, r=50),
                xaxis=dict(
                    categoryorder=(
                        "category ascending"
                        if 기준선택 in ["year_week", "year"]
                        else None
                    ),
                    tickangle=45 if 기준선택 == "year_week" else 0,
                    type="category" if 기준선택 in ["year_week", "year"] else None,
                ),
            )

            st.plotly_chart(fig_bar, use_container_width=True)

        with tab_volume_chart:
            # 그룹별 합계 데이터 생성
            total_by_period = (
                flow.groupby(기준선택)["구매확정물량(톤)"].sum().reset_index()
            )

            # X축 순서 설정 (year_week인 경우 시간순 정렬)
            if 기준선택 == "year_week":
                x_order = sorted(flow[기준선택].unique())
                category_orders = {기준선택: x_order}
            else:
                category_orders = None

            # 누적 막대그래프 생성
            if color_map is None:
                fig_bar = px.bar(
                    flow,
                    x=기준선택,
                    y="구매확정물량(톤)",
                    color=group_col,
                    title=f"{기준선택}별 {group_col}별 거래물량 추이 (단위: 톤)",
                    labels={"구매확정물량(톤)": "거래물량(톤)"},
                    category_orders=category_orders,
                )
            else:
                fig_bar = px.bar(
                    flow,
                    x=기준선택,
                    y="구매확정물량(톤)",
                    color=group_col,
                    title=f"{기준선택}별 {group_col}별 거래물량 추이 (단위: 톤)",
                    labels={"구매확정물량(톤)": "거래물량(톤)"},
                    color_discrete_map=color_map,
                    category_orders=category_orders,
                )

            # 합계 선그래프 추가
            fig_bar.add_scatter(
                x=total_by_period[기준선택],
                y=total_by_period["구매확정물량(톤)"],
                mode="lines+markers",
                name="합계",
                line=dict(color="red", width=3),
                marker=dict(size=8, color="red"),
                yaxis="y",
            )

            # 레이아웃 업데이트
            fig_bar.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=0.95, xanchor="center", x=0.5
                ),
                title=dict(y=0.95, x=0.5, xanchor="center"),
                margin=dict(t=120, b=50, l=50, r=50),
                xaxis=dict(
                    categoryorder=(
                        "category ascending"
                        if 기준선택 in ["year_week", "year"]
                        else None
                    ),
                    tickangle=45 if 기준선택 == "year_week" else 0,
                    type="category" if 기준선택 in ["year_week", "year"] else None,
                ),
            )

            st.plotly_chart(fig_bar, use_container_width=True)

    # 선택된 셀에 대한 거래내역 표시
    _display_transaction_details(
        df,
        기준선택,
        group_col,
        amount_selection,
        volume_selection,
        pivot_amount_with_total,
        pivot_volume_with_total,
    )


# 선택된 셀의 거래내역을 표시하는 함수
def _display_transaction_details(
    df,
    기준선택,
    group_col,
    amount_selection,
    volume_selection,
    pivot_amount_with_total,
    pivot_volume_with_total,
):
    """선택된 피벗 테이블 행에 해당하는 거래내역을 표시"""

    selected_period = None
    table_type = None

    # 금액 테이블에서 선택된 행 처리
    if (
        amount_selection
        and "selection" in amount_selection
        and "rows" in amount_selection["selection"]
    ):
        if amount_selection["selection"]["rows"]:
            selected_row_idx = amount_selection["selection"]["rows"][0]

            # 행 인덱스를 실제 값으로 변환
            if selected_row_idx < len(pivot_amount_with_total.index):
                selected_period = pivot_amount_with_total.index[selected_row_idx]
                table_type = "금액"

    # 물량 테이블에서 선택된 행 처리
    elif (
        volume_selection
        and "selection" in volume_selection
        and "rows" in volume_selection["selection"]
    ):
        if volume_selection["selection"]["rows"]:
            selected_row_idx = volume_selection["selection"]["rows"][0]

            # 행 인덱스를 실제 값으로 변환
            if selected_row_idx < len(pivot_volume_with_total.index):
                selected_period = pivot_volume_with_total.index[selected_row_idx]
                table_type = "물량"

    # 선택된 기간이 있고 "합계" 행이 아닌 경우
    if selected_period and selected_period != "합계":
        _show_filtered_transactions_by_period(
            df,
            기준선택,
            group_col,
            selected_period,
            table_type,
            pivot_amount_with_total,
        )


def _show_filtered_transactions_by_period(
    df, 기준선택, group_col, selected_period, table_type, pivot_amount_with_total
):
    """선택된 기간의 거래내역을 그룹별로 표시"""

    st.markdown("---")

    # 통합 인박스 시작 - HTML div로 전체 감싸기
    # div style="background-color: #F0F8FF; padding: 20px; border-radius: 15px; border: 2px solid #87CEEB; margin: 15px 0;">

    st.markdown(
        f"""
        <div> 
            <h3 style="margin-top: 0; color: #1E6091;">📋 거래내역 상세</h3>
            <p style="margin-bottom: 10px;"><strong>테이블 유형:</strong> {table_type}</p>
            <p style="margin-bottom: 15px;"><strong>선택된 기간:</strong> {selected_period}</p>
        """,
        unsafe_allow_html=True,
    )

    # 해당 기간의 데이터 필터링
    period_data = df[df[기준선택] == selected_period]

    if len(period_data) == 0:
        st.info("해당 기간에 거래내역이 없습니다.")
        return

    # 그룹 선택 UI 추가
    available_groups = sorted(period_data[group_col].dropna().unique())
    if "합계" in available_groups:
        available_groups.remove("합계")

    # 그룹별 거래금액 계산하여 기본값 설정 (가장 큰 거래금액의 그룹)
    group_amounts = (
        period_data.groupby(group_col)["구매확정금액(원)"]
        .sum()
        .sort_values(ascending=False)
    )
    default_group = (
        group_amounts.index[0]
        if len(group_amounts) > 0
        else available_groups[0] if available_groups else None
    )

    if not available_groups:
        st.info("해당 기간에 유효한 그룹이 없습니다.")
        return

    selected_group = st.selectbox(
        f"상세 조회할 {group_col} 선택:",
        options=available_groups,
        index=(
            available_groups.index(default_group)
            if default_group in available_groups
            else 0
        ),
        key=f"group_select_{기준선택}_{selected_period}_{table_type}",
    )

    # 선택된 그룹의 상세 거래내역 표시
    _show_filtered_transactions(
        df, 기준선택, group_col, selected_period, selected_group, table_type
    )

    # 통합 인박스 마감
    st.markdown(
        """
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_filtered_transactions(
    df, 기준선택, group_col, selected_period, selected_group, table_type
):
    """선택된 기간과 그룹에 해당하는 거래내역을 필터링하여 표시"""

    # 그룹 정보 표시
    st.markdown(f"**선택된 {group_col}:** {selected_group}")
    st.markdown("")

    # 데이터 필터링
    filtered_data = df[df[기준선택] == selected_period]
    filtered_data = filtered_data[filtered_data[group_col] == selected_group]

    if len(filtered_data) == 0:
        st.info("해당 조건에 맞는 거래내역이 없습니다.")
        return

    st.markdown("---")

    # 요약 정보 표시
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_amount = filtered_data["구매확정금액(원)"].sum()
        st.metric("총 거래금액", f"{total_amount/1_000_000:,.0f}백만원")
    with col2:
        total_volume = filtered_data["구매확정물량"].sum()
        st.metric("총 거래물량", f"{total_volume/1_000:,.0f}톤")
    with col3:
        transaction_count = len(filtered_data)
        st.metric("거래 건수", f"{transaction_count:,}건")
    with col4:
        unique_products = filtered_data["품목"].nunique()
        st.metric("거래 품목 수", f"{unique_products:,}개")

    st.markdown("---")

    # 판매자/구매자 요약 테이블
    st.markdown("#### 📊 판매자/구매자별 요약")
    st.markdown("")

    # 탭으로 판매자와 구매자 구분
    tab_seller_summary, tab_buyer_summary, tab_seller_buyer_summary = st.tabs(
        ["🏪 판매자별 요약", "🛒 구매자별 요약", "🏪🛒 판매자/구매자별 요약"]
    )

    with tab_seller_summary:
        # 판매자별 요약 계산
        seller_summary = (
            filtered_data.groupby(["판매자", "판매자구분"])
            .agg(
                {
                    "거래유형보정": lambda x: ", ".join(
                        sorted(x.unique())
                    ),  # 거래유형들을 합쳐서 표시
                    "구매확정금액(원)": "sum",
                    "구매확정물량": "sum",
                    "확정일자": "count",  # 거래 건수
                }
            )
            .reset_index()
        )

        # 컬럼명 변경
        seller_summary.columns = [
            "판매자",
            "판매자구분",
            "거래유형보정",
            "구매확정금액(원)",
            "구매확정물량",
            "총거래건수",
        ]

        # 단위 변환
        seller_summary["구매확정금액(백만원)"] = (
            seller_summary["구매확정금액(원)"] / 1_000_000
        ).round(2)
        seller_summary["구매확정물량(톤)"] = (
            seller_summary["구매확정물량"] / 1_000
        ).round(2)

        # 거래금액 기준 내림차순 정렬
        seller_summary = seller_summary.sort_values(
            "구매확정금액(백만원)", ascending=False
        )

        # 표시할 컬럼 선택
        display_seller_cols = [
            "판매자",
            "판매자구분",
            "거래유형보정",
            "구매확정금액(백만원)",
            "구매확정물량(톤)",
            "총거래건수",
        ]

        st.dataframe(
            seller_summary[display_seller_cols].style.format(
                {
                    "구매확정금액(백만원)": "{:,.0f}",
                    "구매확정물량(톤)": "{:,.0f}",
                    "총거래건수": "{:,}",
                }
            ),
            use_container_width=True,
            height=300,
            hide_index=True,
        )

        # 판매자 요약 통계
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 판매자 수", f"{len(seller_summary):,}명")
        with col2:
            avg_amount_per_seller = seller_summary["구매확정금액(백만원)"].mean()
            st.metric("판매자당 평균 거래금액", f"{avg_amount_per_seller:,.0f}백만원")
        with col3:
            avg_transactions_per_seller = seller_summary["총거래건수"].mean()
            st.metric("판매자당 평균 거래건수", f"{avg_transactions_per_seller:,.0f}건")

    with tab_buyer_summary:
        # 구매자별 요약 계산
        buyer_summary = (
            filtered_data.groupby(["구매자", "구매자구분"])
            .agg(
                {
                    "거래유형보정": lambda x: ", ".join(
                        sorted(x.unique())
                    ),  # 거래유형들을 합쳐서 표시
                    "구매확정금액(원)": "sum",
                    "구매확정물량": "sum",
                    "확정일자": "count",  # 거래 건수
                }
            )
            .reset_index()
        )

        # 컬럼명 변경
        buyer_summary.columns = [
            "구매자",
            "구매자구분",
            "거래유형보정",
            "구매확정금액(원)",
            "구매확정물량",
            "총거래건수",
        ]

        # 단위 변환
        buyer_summary["구매확정금액(백만원)"] = (
            buyer_summary["구매확정금액(원)"] / 1_000_000
        ).round(2)
        buyer_summary["구매확정물량(톤)"] = (
            buyer_summary["구매확정물량"] / 1_000
        ).round(2)

        # 거래금액 기준 내림차순 정렬
        buyer_summary = buyer_summary.sort_values(
            "구매확정금액(백만원)", ascending=False
        )

        # 표시할 컬럼 선택
        display_buyer_cols = [
            "구매자",
            "구매자구분",
            "거래유형보정",
            "구매확정금액(백만원)",
            "구매확정물량(톤)",
            "총거래건수",
        ]

        st.dataframe(
            buyer_summary[display_buyer_cols].style.format(
                {
                    "구매확정금액(백만원)": "{:,.0f}",
                    "구매확정물량(톤)": "{:,.0f}",
                    "총거래건수": "{:,}",
                }
            ),
            use_container_width=True,
            height=300,
            hide_index=True,
        )

        # 구매자 요약 통계
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 구매자 수", f"{len(buyer_summary):,}명")
        with col2:
            avg_amount_per_buyer = buyer_summary["구매확정금액(백만원)"].mean()
            st.metric("구매자당 평균 거래금액", f"{avg_amount_per_buyer:,.0f}백만원")
        with col3:
            avg_transactions_per_buyer = buyer_summary["총거래건수"].mean()
            st.metric("구매자당 평균 거래건수", f"{avg_transactions_per_buyer:,.0f}건")

    with tab_seller_buyer_summary:
        # 판매자/구매자별 요약 계산
        seller_buyer_summary = (
            filtered_data.groupby(["판매자", "구매자", "판매자구분", "구매자구분"])
            .agg(
                {
                    "거래유형보정": lambda x: ", ".join(
                        sorted(x.unique())
                    ),  # 거래유형들을 합쳐서 표시
                    "구매확정금액(원)": "sum",
                    "구매확정물량": "sum",
                    "확정일자": "count",  # 거래 건수
                }
            )
            .reset_index()
        )

        # 컬럼명 변경
        seller_buyer_summary.columns = [
            "판매자",
            "구매자",
            "판매자구분",
            "구매자구분",
            "거래유형보정",
            "구매확정금액(원)",
            "구매확정물량",
            "총거래건수",
        ]

        # 단위 변환
        seller_buyer_summary["구매확정금액(백만원)"] = (
            seller_buyer_summary["구매확정금액(원)"] / 1_000_000
        ).round(2)
        seller_buyer_summary["구매확정물량(톤)"] = (
            seller_buyer_summary["구매확정물량"] / 1_000
        ).round(2)

        # 거래금액 기준 내림차순 정렬
        seller_buyer_summary = seller_buyer_summary.sort_values(
            "구매확정금액(백만원)", ascending=False
        )

        # 표시할 컬럼 선택
        display_seller_buyer_cols = [
            "판매자",
            "판매자구분",
            "구매자",
            "구매자구분",
            "거래유형보정",
            "구매확정금액(백만원)",
            "구매확정물량(톤)",
            "총거래건수",
        ]

        st.dataframe(
            seller_buyer_summary[display_seller_buyer_cols].style.format(
                {
                    "구매확정금액(백만원)": "{:,.0f}",
                    "구매확정물량(톤)": "{:,.0f}",
                    "총거래건수": "{:,}",
                }
            ),
            use_container_width=True,
            height=300,
            hide_index=True,
        )

        # 판매자/구매자 요약 통계
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 판매자/구매자 수", f"{len(seller_buyer_summary):,}명")
        with col2:
            avg_amount_per_seller_buyer = seller_buyer_summary[
                "구매확정금액(백만원)"
            ].mean()
            st.metric(
                "판매자/구매자당 평균 거래금액",
                f"{avg_amount_per_seller_buyer:,.0f}백만원",
            )
        with col3:
            avg_transactions_per_seller_buyer = seller_buyer_summary[
                "총거래건수"
            ].mean()
            st.metric(
                "판매자/구매자당 평균 거래건수",
                f"{avg_transactions_per_seller_buyer:,.0f}건",
            )

    st.markdown("---")

    # 거래내역 테이블 표시
    st.markdown("세부 거래내역")

    # 표시할 컬럼 선택
    display_columns = [
        "확정일자",
        "구분",
        "부류",
        "품목",
        "판매자",
        "구매자",
        "판매자구분",
        "구매자구분",
        "거래유형보정",
        "구매확정물량",
        "구매확정금액(원)",
    ]

    # 존재하는 컬럼만 선택
    available_columns = [col for col in display_columns if col in filtered_data.columns]
    display_data = filtered_data[available_columns].copy()

    # 금액과 물량 포맷팅
    if "구매확정금액(원)" in display_data.columns:
        display_data["구매확정금액(백만원)"] = (
            display_data["구매확정금액(원)"] / 1_000_000
        ).round(0)
    if "구매확정물량" in display_data.columns:
        display_data["구매확정물량(톤)"] = (display_data["구매확정물량"] / 1_000).round(
            0
        )

    # 정렬 (최신 거래부터)
    if "확정일자" in display_data.columns:
        display_data = display_data.sort_values("확정일자", ascending=False)

    # 페이징 처리
    items_per_page = st.selectbox(
        "페이지당 표시 건수",
        [10, 25, 50, 100],
        index=1,
        key=f"pagination_{기준선택}_{group_col}_{selected_period}_{selected_group}",
    )

    total_items = len(display_data)
    total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1

    if total_pages > 1:
        page = st.selectbox(
            f"페이지 선택 (총 {total_pages}페이지, {total_items}건)",
            range(1, total_pages + 1),
            key=f"page_{기준선택}_{group_col}_{selected_period}_{selected_group}",
        )
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        paginated_data = display_data.iloc[start_idx:end_idx]
        st.caption(f"전체 {total_items}건 중 {start_idx + 1}-{end_idx}건 표시")
    else:
        paginated_data = display_data
        st.caption(f"전체 {total_items}건 표시")

    # 테이블 표시
    st.dataframe(paginated_data, use_container_width=True, height=400, hide_index=True)

    # 데이터 다운로드 기능
    # if len(display_data) > 0:
    #     csv = display_data.to_csv(index=False, encoding="utf-8-sig")
    #     st.download_button(
    #         label="📥 거래내역 CSV 다운로드",
    #         data=csv,
    #         file_name=f"거래내역_{selected_period}_{selected_group}_{table_type}.csv",
    #         mime="text/csv",
    #         key=f"download_{기준선택}_{group_col}_{selected_period}_{selected_group}_{table_type}",
    #     )


# 메인 실행
def main():
    st.title("🛒 거래 KPI 대시보드")
    df = load_and_process_data()
    df = add_date_columns(df)
    (
        기준선택,
        date_range,
        selected_구분,
        exclude_rice,
        selected_부류,
        selected_품목,
        selected_seller_type,
        selected_seller_dtl_type,
        selected_buyer_type,
        selected_trade_type,
        top_n,
        show_row_total,
        show_col_total,
    ) = create_sidebar_filters(df)
    # 전체 누계 KPI
    display_kpi_section(df, "주요 KPI", "전체 누계")
    # display_kpi_2025_section(df["확정일자"].dt.year == 2025, "주요 KPI", "2025년")
    # 필터 적용
    filtered_df = filter_data(
        df,
        date_range,
        selected_구분,
        exclude_rice,
        selected_부류,
        selected_품목,
        selected_seller_type,
        selected_seller_dtl_type,
        selected_buyer_type,
        selected_trade_type,
    )

    # 선택된 기간 내 데이터가 없으면 메시지 표시
    if filtered_df.empty:
        st.warning("선택한 조회기간 내 데이터가 없습니다. 다른 기간을 선택해주세요.")

    # 조회기간 KPI
    display_kpi_period_section(filtered_df, "주요 KPI", "조회 기간")

    # ================= 인사이트(요약) 섹션 =================
    st.markdown("##  요약")

    if not filtered_df.empty:
        기준선택 = (
            st.session_state["기준선택"]
            if "기준선택" in st.session_state
            else "year_month"
        )
        year = filtered_df["확정일자"].dt.year.mode()[0]
        year_df = filtered_df[filtered_df["확정일자"].dt.year == year]

        # 1.1 총 매출액 및 연말 예상 매출액
        total_amt = year_df["구매확정금액(원)"].sum()
        min_date = year_df["확정일자"].min()
        max_date = year_df["확정일자"].max()
        days = (max_date - min_date).days + 1
        daily_avg = total_amt / days if days > 0 else 0
        from datetime import datetime

        end_of_year = datetime(year, 12, 31)
        days_left = (end_of_year - max_date).days
        days_left = max(days_left, 0)
        expected_amt = total_amt + (daily_avg * days_left)

        # 2. 기준선택별 구분별 매출액 및 전기대비 증감률 (글 요약)
        group_col = "구분"
        pivot = (
            year_df.groupby([기준선택, group_col])["구매확정금액(원)"]
            .sum()
            .unstack()
            .fillna(0)
        )
        pct_df = pivot.pct_change().fillna(0) * 100
        last_idx = pivot.index[-1]
        last_row = pivot.loc[last_idx]
        last_pct = pct_df.loc[last_idx]

        # 요약 텍스트 생성
        summary_text = f"{year}년 {기준선택}별 매출액은 총 {total_amt/1_000_000:,.0f}백만원, <br>연말까지 {expected_amt/1_000_000:,.0f}백만원 예상.<br>"
        for g in last_row.index:
            summary_text += f"- {g} 매출액: {last_row[g]/1_000_000:,.0f}백만원 (전기대비 {last_pct[g]:,.1f}%)<br>"

        # 토글 형식으로 표시
        with st.expander(" 매출 요약 보기", expanded=False):
            st.markdown(
                f"<div style='font-size:1.5em'>{summary_text}</div>",
                unsafe_allow_html=True,
            )

        # 상위 거래품목/증가/감소 품목 Top10을 토글 형식으로 표시
        with st.expander(" 품목별 거래 TOP 10", expanded=False):
            # 3~4. 상위 거래품목/증가/감소 품목 Top10을 1행 3열로 배치
            col_top, col_inc, col_dec = st.columns(3)

            # 상위 거래 품목 Top 10
            with col_top:
                st.markdown(f"####  상위 거래 품목 Top 10")
                top_items = (
                    year_df.groupby("품목")["구매확정금액(원)"].sum().reset_index()
                )
                top_items = top_items.sort_values(
                    "구매확정금액(원)", ascending=False
                ).head(10)
                top_items["구매확정금액(백만원)"] = (
                    top_items["구매확정금액(원)"] / 1_000_000
                ).round(0)
                st.dataframe(
                    top_items[["품목", "구매확정금액(백만원)"]]
                    .reset_index(drop=True)
                    .style.format({"구매확정금액(백만원)": "{:,.0f}"})
                )

            # 증감 품목 Top 10 (증감금액, 증감률)
            item_pivot = (
                year_df.groupby([기준선택, "품목"])["구매확정금액(원)"]
                .sum()
                .reset_index()
            )
            기준값s = sorted(year_df[기준선택].unique())
            if len(기준값s) >= 2:
                prev, curr = 기준값s[-2], 기준값s[-1]
                prev_items = item_pivot[item_pivot[기준선택] == prev].set_index("품목")
                curr_items = item_pivot[item_pivot[기준선택] == curr].set_index("품목")
                merged_items = (
                    curr_items[["구매확정금액(원)"]]
                    .join(
                        prev_items[["구매확정금액(원)"]],
                        lsuffix="_curr",
                        rsuffix="_prev",
                        how="outer",
                    )
                    .fillna(0)
                )
                merged_items["증감금액(원)"] = (
                    merged_items["구매확정금액(원)_curr"]
                    - merged_items["구매확정금액(원)_prev"]
                )
                merged_items["증감률(%)"] = merged_items.apply(
                    lambda row: (
                        (row["증감금액(원)"] / row["구매확정금액(원)_prev"] * 100)
                        if row["구매확정금액(원)_prev"] != 0
                        else 0
                    ),
                    axis=1,
                )
                merged_items["증감금액(백만원)"] = (
                    merged_items["증감금액(원)"] / 1_000_000
                ).round(0)
                merged_items["매출액(백만원)"] = (
                    merged_items["구매확정금액(원)_curr"] / 1_000_000
                ).round(0)
                merged_items["증감률(%)"] = (
                    merged_items["증감률(%)"]
                    .replace([float("inf"), float("-inf")], 0)
                    .round(1)
                    .fillna(0)
                )
                merged_items = merged_items.reset_index().rename(
                    columns={
                        "품목": "품목",
                        "매출액(백만원)": "매출액(백만원)",
                        "증감금액(백만원)": "증감금액(백만원)",
                        "증감률(%)": "증감률(%)",
                    }
                )
                # 증가 Top 10
                with col_inc:
                    st.markdown("**증가 품목 Top 10**")
                    inc10 = merged_items.sort_values(
                        "증감금액(원)", ascending=False
                    ).head(10)
                    st.dataframe(
                        inc10[
                            ["품목", "매출액(백만원)", "증감금액(백만원)", "증감률(%)"]
                        ].style.format(
                            {
                                "매출액(백만원)": "{:,.0f}",
                                "증감금액(백만원)": "{:,.0f}",
                                "증감률(%)": "{:+.1f}",
                            }
                        )
                    )
                # 감소 Top 10
                with col_dec:
                    st.markdown("**감소 품목 Top 10**")
                    dec10 = merged_items.sort_values(
                        "증감금액(원)", ascending=True
                    ).head(10)
                    st.dataframe(
                        dec10[
                            ["품목", "매출액(백만원)", "증감금액(백만원)", "증감률(%)"]
                        ].style.format(
                            {
                                "매출액(백만원)": "{:,.0f}",
                                "증감금액(백만원)": "{:,.0f}",
                                "증감률(%)": "{:+.1f}",
                            }
                        )
                    )
            else:
                with col_inc:
                    st.info("증감률 계산을 위해 2개 이상의 기간이 필요합니다.")
                with col_dec:
                    st.info("")
    else:
        st.info("조회된 데이터가 없습니다.")

    # ================= 거래 분석 세션 =================
    display_item_analysis(
        filtered_df,
        top_n=top_n,
        show_row_total=show_row_total,
        show_col_total=show_col_total,
    )


if __name__ == "__main__":
    main()
