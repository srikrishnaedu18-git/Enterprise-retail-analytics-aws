"""
Enterprise Retail Analytics Platform — BI Dashboard
=====================================================
Cloud-Native Lakehouse Intelligence Layer (S3 + Athena + Streamlit)

Queries live Apache Parquet tables stored in the Titan Retail Data Lake
on Amazon S3 via Amazon Athena. Renders KPI metrics and interactive
Plotly visualisations with category-level sidebar filtering.

Author : Sri Krishna
Stack  : Streamlit · PyAthena · Plotly Express · Pandas
"""

# ──────────────────────────────────────────────
# 1. IMPORTS
# ──────────────────────────────────────────────
import os
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
from psycopg2 import OperationalError as Psycopg2OperationalError
from pyathena import connect
from pyathena.error import OperationalError, DatabaseError

# ──────────────────────────────────────────────
# 2. GLOBAL CONFIGURATIONS
# ──────────────────────────────────────────────
AWS_REGION = "us-east-1"
ATHENA_DATABASE = "titan_retail_processed_db"
ATHENA_S3_STAGING = "s3://titan-retail-datalake-srikrishna/athena-results/"


def wait_for_db(host, user, password, dbname, port, retries=5, delay=3):
    """Gracefully wait for PostgreSQL to accept connections before continuing."""
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                dbname=dbname,
                port=port,
            )
            conn.close()
            return True
        except Psycopg2OperationalError as exc:
            print(f"Database connection attempt {attempt} failed: {exc}")
            if attempt < retries:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
    return False


def startup_event():
    """Fetch environment variables and ensure PostgreSQL is reachable before the app continues."""
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "postgres")
    db_port = int(os.getenv("DB_PORT", "5432"))

    if not wait_for_db(db_host, db_user, db_password, db_name, db_port):
        raise RuntimeError("Could not connect to the database after multiple retries.")

# ──────────────────────────────────────────────
# 3. STREAMLIT PAGE CONFIGURATION
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Retail Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    startup_event()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

# ──────────────────────────────────────────────
# 4. CUSTOM CSS — Premium Dark Theme
# ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Root overrides ── */
    :root {
        --bg-primary: #0e1117;
        --bg-card: rgba(30, 34, 46, 0.75);
        --accent-blue: #4fc3f7;
        --accent-purple: #b388ff;
        --accent-green: #69f0ae;
        --accent-amber: #ffd54f;
        --text-primary: #e0e0e0;
        --text-muted: #9e9e9e;
        --glass-border: rgba(255, 255, 255, 0.08);
    }

    /* ── Global body ── */
    .stApp {
        background: linear-gradient(145deg, #0e1117 0%, #1a1f2e 50%, #0e1117 100%);
    }

    /* ── Header banner ── */
    .dashboard-header {
        background: linear-gradient(135deg, rgba(79, 195, 247, 0.12) 0%, rgba(179, 136, 255, 0.12) 100%);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(12px);
    }
    .dashboard-header h1 {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4fc3f7, #b388ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .dashboard-header p {
        color: var(--text-muted);
        font-size: 0.95rem;
        margin: 0;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--glass-border);
        border-radius: 14px;
        padding: 1.5rem 1.25rem;
        backdrop-filter: blur(10px);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        text-align: center;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 32px rgba(79, 195, 247, 0.15);
    }
    .metric-card .metric-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: var(--text-muted);
        margin-bottom: 0.35rem;
    }
    .metric-card .metric-value {
        font-family: 'Inter', sans-serif;
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0;
    }
    .blue  .metric-value { color: var(--accent-blue); }
    .purple .metric-value { color: var(--accent-purple); }
    .green .metric-value { color: var(--accent-green); }
    .amber .metric-value { color: var(--accent-amber); }

    /* ── Chart containers ── */
    .chart-container {
        background: var(--bg-card);
        border: 1px solid var(--glass-border);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    .chart-container h3 {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    /* ── Sidebar styling ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #151922 0%, #1a1f2e 100%);
        border-right: 1px solid var(--glass-border);
    }
    section[data-testid="stSidebar"] .stSelectbox label {
        color: var(--text-primary) !important;
        font-weight: 600;
    }

    /* ── Footer ── */
    .footer-bar {
        text-align: center;
        color: var(--text-muted);
        font-size: 0.75rem;
        padding: 1.5rem 0 0.75rem 0;
        border-top: 1px solid var(--glass-border);
        margin-top: 2rem;
    }

    /* ── Hide default Streamlit menu & footer ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# 5. ATHENA QUERY EXECUTOR (CACHED)
# ──────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def run_athena_query(query: str) -> pd.DataFrame:
    """
    Execute a SQL query against Amazon Athena and return the result as a
    Pandas DataFrame.  Results are cached for 10 minutes (TTL = 600 s)
    to minimise Athena scan costs and reduce latency on repeat loads.
    """
    conn = connect(
        region_name=AWS_REGION,
        s3_staging_dir=ATHENA_S3_STAGING,
        schema_name=ATHENA_DATABASE,
    )
    df = pd.read_sql(query, conn)
    return df


# ──────────────────────────────────────────────
# 6. UNIFIED SQL JOIN — Core Data Layer
# ──────────────────────────────────────────────
MASTER_QUERY = """
SELECT
    s.transaction_id,
    s.date,
    s.store_id,
    s.customer_id,
    s.product_id,
    s.quantity,
    s.price              AS sale_price,
    (s.quantity * s.price) AS revenue,
    p.category,
    p.brand,
    p.cost               AS product_cost,
    p.price              AS product_price,
    c.name               AS customer_name,
    c.city,
    c.age,
    c.gender
FROM sales   AS s
INNER JOIN products  AS p ON s.product_id  = p.product_id
INNER JOIN customers AS c ON s.customer_id = c.customer_id
"""


# ──────────────────────────────────────────────
# 7. HEADER
# ──────────────────────────────────────────────
st.markdown(
    """
    <div class="dashboard-header">
        <h1>📊 Enterprise Retail Analytics Platform</h1>
        <p>Cloud-Native Lakehouse Intelligence Layer &nbsp;·&nbsp; S3 + Athena + Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# 8. DATA RETRIEVAL + ERROR BOUNDARY
# ──────────────────────────────────────────────
try:
    with st.spinner("⏳ Querying AWS Athena — scanning Parquet tables in S3…"):
        df = run_athena_query(MASTER_QUERY)

    # Parse the date field into a proper datetime object
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

except (OperationalError, DatabaseError) as athena_err:
    st.error(
        f"**Athena Connection Error**\n\n"
        f"`{athena_err}`\n\n"
        "Ensure your AWS credentials are configured correctly.  "
        "Run `aws configure` or set up your `~/.aws/credentials` file with a valid "
        "`aws_access_key_id` and `aws_secret_access_key` for the **us-east-1** region."
    )
    st.stop()

except Exception as exc:
    st.error(
        f"**Unexpected Error**\n\n"
        f"`{type(exc).__name__}: {exc}`\n\n"
        "Please verify your AWS credentials (`~/.aws/credentials`) and ensure the "
        "Athena database **titan_retail_processed_db** and its tables (sales, products, "
        "customers) exist in the Glue Data Catalog."
    )
    st.stop()


# ──────────────────────────────────────────────
# 9. SIDEBAR — Category Filter
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Dashboard Controls")
    st.markdown("---")

    categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
    selected_category = st.selectbox(
        "Filter by Product Category",
        options=categories,
        index=0,
        help="Select a product category to filter all charts and KPIs.",
    )

    st.markdown("---")
    st.info(
        "💡 **Serverless Analytics**\n\n"
        "All queries execute directly on **Amazon Athena** — a serverless, "
        "interactive query service that scans Parquet data stored in your "
        "S3 Data Lake. No infrastructure to manage."
    )

    st.markdown("---")
    st.caption(f"📅 Data range: {df['date'].min():%Y-%m-%d} → {df['date'].max():%Y-%m-%d}")
    st.caption(f"📦 Rows loaded: {len(df):,}")

# Apply filter
if selected_category != "All":
    filtered_df = df[df["category"] == selected_category].copy()
else:
    filtered_df = df.copy()


# ──────────────────────────────────────────────
# 10. KEY BUSINESS METRICS
# ──────────────────────────────────────────────
total_revenue = filtered_df["revenue"].sum()
total_orders = filtered_df["transaction_id"].nunique()
total_items = filtered_df["quantity"].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(
        f"""
        <div class="metric-card blue">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">₹{total_revenue:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
        <div class="metric-card purple">
            <div class="metric-label">Total Orders</div>
            <div class="metric-value">{total_orders:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
        <div class="metric-card green">
            <div class="metric-label">Items Sold</div>
            <div class="metric-value">{total_items:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        f"""
        <div class="metric-card amber">
            <div class="metric-label">Avg Order Value</div>
            <div class="metric-value">₹{avg_order_value:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 11. PLOTLY CHART THEME
# ──────────────────────────────────────────────
CHART_TEMPLATE = "plotly_dark"
CHART_BG = "rgba(0,0,0,0)"
CHART_PAPER_BG = "rgba(0,0,0,0)"
CHART_FONT = dict(family="Inter, sans-serif", size=12, color="#b0b0b0")
CHART_COLORSCALE = px.colors.sequential.Tealgrn
BRAND_PALETTE = [
    "#4fc3f7", "#b388ff", "#69f0ae", "#ffd54f",
    "#ff8a80", "#80deea", "#ce93d8", "#a5d6a7",
    "#fff176", "#ef9a9a", "#90caf9", "#f48fb1",
]


def style_figure(fig, margin_l=40, margin_r=20, margin_t=30, margin_b=40):
    """Apply the unified dark glassmorphism theme to a Plotly figure."""
    fig.update_layout(
        template=CHART_TEMPLATE,
        paper_bgcolor=CHART_PAPER_BG,
        plot_bgcolor=CHART_BG,
        font=CHART_FONT,
        margin=dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#b0b0b0"),
        ),
        hoverlabel=dict(
            bgcolor="#1e222e",
            font_size=12,
            font_family="Inter, sans-serif",
        ),
    )
    return fig


# ──────────────────────────────────────────────
# 12. ANALYTICAL CHARTS — 2 × 2 Grid
# ──────────────────────────────────────────────

# ── Row 1 ──
col_left, col_right = st.columns(2)

# Chart 1: Daily Revenue Trends
with col_left:
    st.markdown('<div class="chart-container"><h3>📈 Daily Revenue Trends</h3>', unsafe_allow_html=True)
    daily_rev = (
        filtered_df.groupby(filtered_df["date"].dt.date)["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"date": "Date", "revenue": "Revenue"})
        .sort_values("Date")
    )
    fig_line = px.line(
        daily_rev,
        x="Date",
        y="Revenue",
        markers=True,
        color_discrete_sequence=["#4fc3f7"],
    )
    fig_line.update_traces(
        line=dict(width=2.5),
        marker=dict(size=5),
        fill="tozeroy",
        fillcolor="rgba(79,195,247,0.08)",
        hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.2f}<extra></extra>",
    )
    style_figure(fig_line)
    st.plotly_chart(fig_line, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

# Chart 2: Brand Value Distribution
with col_right:
    st.markdown('<div class="chart-container"><h3>🏷️ Brand Value Distribution</h3>', unsafe_allow_html=True)
    brand_rev = (
        filtered_df.groupby("brand")["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"brand": "Brand", "revenue": "Revenue"})
        .sort_values("Revenue", ascending=True)
    )
    fig_bar = px.bar(
        brand_rev,
        x="Revenue",
        y="Brand",
        orientation="h",
        color="Revenue",
        color_continuous_scale=["#1a1f2e", "#4fc3f7", "#b388ff"],
    )
    fig_bar.update_traces(
        hovertemplate="<b>%{y}</b><br>Revenue: ₹%{x:,.2f}<extra></extra>",
    )
    fig_bar.update_layout(coloraxis_showscale=False)
    style_figure(fig_bar)
    st.plotly_chart(fig_bar, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

# ── Row 2 ──
col_left2, col_right2 = st.columns(2)

# Chart 3: Regional Revenue Split
with col_left2:
    st.markdown('<div class="chart-container"><h3>🌍 Regional Revenue Split</h3>', unsafe_allow_html=True)
    city_rev = (
        filtered_df.groupby("city")["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"city": "City", "revenue": "Revenue"})
        .sort_values("Revenue", ascending=False)
    )
    fig_pie = px.pie(
        city_rev,
        values="Revenue",
        names="City",
        hole=0.50,
        color_discrete_sequence=BRAND_PALETTE,
    )
    fig_pie.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>",
    )
    style_figure(fig_pie, margin_t=10, margin_b=10)
    st.plotly_chart(fig_pie, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

# Chart 4: Channel Ingestion Breakdown (Store-level)
with col_right2:
    st.markdown('<div class="chart-container"><h3>🏬 Channel Ingestion Breakdown</h3>', unsafe_allow_html=True)
    store_rev = (
        filtered_df.groupby("store_id")["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"store_id": "Store", "revenue": "Revenue"})
        .sort_values("Revenue", ascending=True)
    )
    store_rev["Store"] = store_rev["Store"].astype(str)
    fig_hbar = px.bar(
        store_rev,
        x="Revenue",
        y="Store",
        orientation="h",
        color="Revenue",
        color_continuous_scale=["#1a1f2e", "#69f0ae", "#ffd54f"],
    )
    fig_hbar.update_traces(
        hovertemplate="<b>Store %{y}</b><br>Revenue: ₹%{x:,.2f}<extra></extra>",
    )
    fig_hbar.update_layout(coloraxis_showscale=False)
    style_figure(fig_hbar)
    st.plotly_chart(fig_hbar, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 13. AI DEMAND FORECASTING (SAGEMAKER INTEGRATION)
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="chart-container" style="border-left: 3px solid #4fc3f7;">
        <h3>🤖 ML Demand Forecasting — 7-Day Outlook</h3>
        <p style="color: #9e9e9e; font-size: 0.85rem; margin: 0;">
            Powered by AWS SageMaker Random Forest Regressor &nbsp;·&nbsp;
            Predictions pulled from the S3 Analytics Zone
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    import boto3
    from io import StringIO

    # Pull the forecast CSV from the S3 Analytics Zone via boto3
    s3_client = boto3.client("s3")
    forecast_obj = s3_client.get_object(
        Bucket="titan-retail-datalake-srikrishna",
        Key="analytics/forecast/7_day_forecast.csv",
    )
    forecast_csv = forecast_obj["Body"].read().decode("utf-8")
    forecast_df = pd.read_csv(StringIO(forecast_csv))

    # Parse the date column
    forecast_df["date"] = pd.to_datetime(forecast_df["date"], errors="coerce")

    # Product selector for forecast view
    product_list = sorted(forecast_df["product_id"].unique().tolist())
    selected_product = st.selectbox(
        "🔎 Select Product to view demand forecast",
        options=product_list,
        help="Choose a product ID to see its 7-day predicted demand.",
    )

    # Filter for the selected product
    prod_forecast = forecast_df[forecast_df["product_id"] == selected_product].copy()

    # Forecast chart
    forecast_col1, forecast_col2 = st.columns([2, 1])

    with forecast_col1:
        st.markdown(
            '<div class="chart-container"><h3>📈 Predicted Unit Demand</h3>',
            unsafe_allow_html=True,
        )
        fig_forecast = px.line(
            prod_forecast,
            x="date",
            y="predicted_demand",
            markers=True,
            color_discrete_sequence=["#4fc3f7"],
        )
        fig_forecast.update_traces(
            line=dict(width=3),
            marker=dict(size=8, symbol="diamond", color="#b388ff"),
            fill="tozeroy",
            fillcolor="rgba(79,195,247,0.06)",
            hovertemplate="<b>%{x|%b %d}</b><br>Predicted Demand: %{y:,.0f} units<extra></extra>",
        )
        style_figure(fig_forecast)
        fig_forecast.update_layout(
            xaxis_title="Future Date",
            yaxis_title="Predicted Units to Stock",
        )
        st.plotly_chart(fig_forecast, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

    with forecast_col2:
        st.markdown(
            '<div class="chart-container"><h3>📋 Forecast Summary</h3>',
            unsafe_allow_html=True,
        )
        total_predicted = prod_forecast["predicted_demand"].sum()
        avg_predicted = prod_forecast["predicted_demand"].mean()
        peak_day = prod_forecast.loc[prod_forecast["predicted_demand"].idxmax()]

        st.markdown(
            f"""
            <div class="metric-card blue" style="margin-bottom: 0.75rem;">
                <div class="metric-label">Total 7-Day Demand</div>
                <div class="metric-value" style="font-size: 1.4rem;">{total_predicted:,.0f} units</div>
            </div>
            <div class="metric-card purple" style="margin-bottom: 0.75rem;">
                <div class="metric-label">Avg Daily Demand</div>
                <div class="metric-value" style="font-size: 1.4rem;">{avg_predicted:,.1f} units</div>
            </div>
            <div class="metric-card amber" style="margin-bottom: 0.75rem;">
                <div class="metric-label">Peak Demand Day</div>
                <div class="metric-value" style="font-size: 1.2rem;">{peak_day['date']:%b %d} — {peak_day['predicted_demand']:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Expandable raw ML output
    with st.expander("📊 View Raw Machine Learning Output"):
        st.dataframe(prod_forecast, use_container_width=True)

except Exception as e:
    st.info(
        "⏳ **ML Pipeline Pending**\n\n"
        "The Machine Learning forecasting pipeline has not executed yet. "
        "Run the SageMaker notebook to generate the `7_day_forecast.csv` "
        "in `s3://titan-retail-datalake-srikrishna/analytics/forecast/`."
    )


# ──────────────────────────────────────────────
# 14. FOOTER
# ──────────────────────────────────────────────
st.markdown(
    """
    <div class="footer-bar">
        Enterprise Retail Analytics Platform &nbsp;·&nbsp;
        Powered by Amazon S3, Athena, SageMaker &amp; Streamlit &nbsp;·&nbsp;
        © 2026 Titan Analytics
    </div>
    """,
    unsafe_allow_html=True,
)

#http://34.229.20.5:8501/