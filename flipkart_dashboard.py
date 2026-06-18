# flipkart_dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import pdfplumber
from io import BytesIO


st.set_page_config(page_title="Flipkart Order Analytics", layout="wide")
sns.set(style="whitegrid")

st.markdown("""
<h1 style='text-align:center; color:#2874F0;'>
📊 Flipkart Business Analytics Dashboard
</h1>
<h4 style='text-align:center; color:black;'>
Sales • Revenue • Customer Insights • Delivery Analytics
</h4>
""", unsafe_allow_html=True)
st.markdown("Upload an orders CSV to explore categories, spending, delivery times and trends.")

# ---------- Helper functions ----------
@st.cache_data
def load_sample():
    # if you want a built-in small sample
    data = {
        'order_id':[101,102,103,104,105,106,107,108,109,110],
        'customer_id':[1,2,3,2,4,5,3,6,7,4],
        'category':['Electronics','Clothing','Mobiles','Mobiles','Home','Clothing','Electronics','Books','Books','Home'],
        'price':[15000,1200,18000,17000,2500,900,15500,400,350,2000],
        'quantity':[1,2,1,1,1,3,1,2,1,1],
        'order_date':['2024-06-01','2024-06-02','2024-06-03','2024-06-03','2024-06-04','2024-06-04','2024-06-05','2024-06-06','2024-06-06','2024-06-07'],
        'delivery_date':['2024-06-04','2024-06-05','2024-06-06','2024-06-06','2024-06-07','2024-06-06','2024-06-09','2024-06-08','2024-06-09','2024-06-10'],
        'payment_type':['UPI','Card','COD','UPI','COD','UPI','Card','COD','UPI','UPI']
    }
    return pd.DataFrame(data)

def preprocess(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    # required columns safe-check
    if 'order_date' in df.columns:
        df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    if 'delivery_date' in df.columns:
        df['delivery_date'] = pd.to_datetime(df['delivery_date'], errors='coerce')
        df['delivery_days'] = (df['delivery_date'] - df['order_date']).dt.days
    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
    if 'quantity' in df.columns:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
    if 'price' in df.columns and 'quantity' in df.columns:
        df['total_amount'] = df['price'] * df['quantity']
    return df

def to_csv_bytes(df):
    return df.to_csv(index=False).encode('utf-8')

# ---------- Sidebar: upload + options ----------
st.sidebar.header("Upload & Options")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv', 'pdf', 'xlsx'])
use_sample = st.sidebar.checkbox("Use sample dataset", value=False)

if use_sample:
    df = load_sample()

elif uploaded_file is not None:

    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)

    elif uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)

    elif uploaded_file.name.endswith('.pdf'):

        tables = []

        with pdfplumber.open(uploaded_file) as pdf:

            for page in pdf.pages:

                table = page.extract_table()

                if table:
                    tables.extend(table)

        if tables:
            df = pd.DataFrame(tables[1:], columns=tables[0])
        else:
            st.error("No table found in PDF")
            st.stop()

# preprocess
if 'df' in locals():
    df = preprocess(df)
else:
    st.error("Could not load file correctly")
    st.stop()

# ---------- Filters ----------
st.sidebar.markdown("### Filters")
if 'order_date' in df.columns:
    min_date = df['order_date'].min()
    max_date = df['order_date'].max()
    date_range = st.sidebar.date_input("Order Date range", value=(min_date, max_date))
    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df = df[(df['order_date'] >= start_date) & (df['order_date'] <= end_date)]
else:
    st.sidebar.write("No order_date column detected.")

category_list = df['category'].unique().tolist() if 'category' in df.columns else []
selected_categories = st.sidebar.multiselect("Category", options=category_list, default=category_list)

if selected_categories:
    df = df[df['category'].isin(selected_categories)]

payment_list = df['payment_type'].unique().tolist() if 'payment_type' in df.columns else []
selected_payments = st.sidebar.multiselect("Payment Type", options=payment_list, default=payment_list)
if selected_payments:
    df = df[df['payment_type'].isin(selected_payments)]

# ---------- Top metrics ----------
st.subheader("Key Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Orders", int(df['order_id'].nunique()) if 'order_id' in df.columns else len(df))
col2.metric("Unique Customers", int(df['customer_id'].nunique()) if 'customer_id' in df.columns else "-")
col3.metric("Average Delivery Days", round(df['delivery_days'].mean(), 2) if 'delivery_days' in df.columns else "-")
col4.metric("Total Revenue (₹)", int(df['total_amount'].sum()) if 'total_amount' in df.columns else 0)

st.markdown("---")

# ---------- Tabs ----------

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🤖 AI Insights",
    "🔮 Forecast",
    "📄 Reports"
])

# ===========================
# DASHBOARD TAB
# ===========================

with tab1:

    # Top categories
    if 'category' in df.columns:
        st.subheader("📦 Most Ordered Categories")

        cat_counts = df['category'].value_counts().reset_index()
        cat_counts.columns = ['category','orders']

        fig = px.bar(
            cat_counts,
            x='orders',
            y='category',
            orientation='h',
            color='orders',
            title="Orders by Category"
        )

        st.plotly_chart(fig, use_container_width=True)

    # Spending by category
    if 'total_amount' in df.columns and 'category' in df.columns:

        st.subheader("💰 Revenue by Category")

        spend = (
            df.groupby('category', as_index=False)
            ['total_amount']
            .sum()
            .sort_values('total_amount', ascending=False)
        )

        fig2 = px.bar(
            spend,
            x='category',
            y='total_amount',
            color='total_amount'
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Orders Over Time
    if 'order_date' in df.columns:

        st.subheader("📈 Orders Over Time")

        time_series = (
            df.groupby(df['order_date'].dt.date)
            .size()
            .reset_index(name='orders')
        )

        fig3 = px.area(
            time_series,
            x='order_date',
            y='orders'
        )

        st.plotly_chart(fig3, use_container_width=True)

    # Payment Methods
    if 'payment_type' in df.columns:

        st.subheader("💳 Payment Distribution")

        pay = df['payment_type'].value_counts().reset_index()

        pay.columns = ['payment_type','count']

        fig5 = px.pie(
            pay,
            names='payment_type',
            values='count'
        )

        st.plotly_chart(fig5, use_container_width=True)

# ===========================
# AI INSIGHTS TAB
# ===========================

with tab2:

    st.subheader("🤖 AI Business Insights")

    if st.button("Generate AI Insights"):

        top_category = (
            df.groupby('category')['total_amount']
            .sum()
            .idxmax()
        )

        top_payment = df['payment_type'].mode()[0]

        avg_delivery = round(
            df['delivery_days'].mean(),
            2
        )

        revenue = int(df['total_amount'].sum())

        st.success(f"""
🏆 Top Revenue Category: {top_category}

💳 Most Preferred Payment: {top_payment}

🚚 Average Delivery Time: {avg_delivery} Days

💰 Total Revenue: ₹{revenue:,}
""")

        st.info("""
💡 Recommendation:

• Increase stock for top performing category.

• Promote digital payments.

• Improve logistics for faster delivery.
""")

# ===========================
# FORECAST TAB
# ===========================

with tab3:

    st.subheader("🔮 AI Sales Forecast")

    revenue = int(df['total_amount'].sum())

    forecast = int(revenue * 1.15)

    st.metric(
        "Predicted Next Month Revenue",
        f"₹{forecast:,}"
    )

    st.warning(
        "Simple AI forecast based on growth trend."
    )

# ===========================
# REPORTS TAB
# ===========================

with tab4:

    st.subheader("📄 Download Reports")

    csv_bytes = to_csv_bytes(df)

    st.download_button(
        "📥 Download Filtered CSV",
        csv_bytes,
        file_name="filtered_orders.csv",
        mime="text/csv"
    )

    st.dataframe(df.head(50))
# Top categories
if 'category' in df.columns:
    st.subheader("Most Ordered Categories")
    cat_counts = df['category'].value_counts().reset_index()
    cat_counts.columns = ['category','orders']
    fig = px.bar(cat_counts, x='orders', y='category', orientation='h', title="Orders by Category")
    st.plotly_chart(fig, use_container_width=True)

# Spending by category
if 'total_amount' in df.columns and 'category' in df.columns:
    st.subheader("Spending by Category")
    spend = df.groupby('category', as_index=False)['total_amount'].sum().sort_values('total_amount', ascending=False)
    fig2 = px.bar(spend, x='category', y='total_amount', title='Total Revenue by Category')
    st.plotly_chart(fig2, use_container_width=True)

# Orders over time
if 'order_date' in df.columns:
    st.subheader("Orders Over Time")
    time_series = df.groupby(df['order_date'].dt.date).size().reset_index(name='orders')
    fig3 = px.line(time_series, x='order_date', y='orders', markers=True, title='Orders Over Time')
    st.plotly_chart(fig3, use_container_width=True)

# Delivery time distribution
if 'delivery_days' in df.columns:
    st.subheader("Delivery Time Distribution (days)")
    fig4 = px.histogram(df, x='delivery_days', nbins=10, title='Delivery Days Histogram')
    st.plotly_chart(fig4, use_container_width=True)

# Payment method pie
if 'payment_type' in df.columns:
    st.subheader("Payment Methods")
    pay = df['payment_type'].value_counts().reset_index()
    pay.columns = ['payment_type','count']
    fig5 = px.pie(pay, names='payment_type', values='count', title='Payment Method Distribution')
    st.plotly_chart(fig5, use_container_width=True)

    # ---------- AI Business Insights ----------

st.subheader("🤖 AI Business Insights")

if st.button("Generate Business Insights"):

    insights = []

    if 'category' in df.columns and 'total_amount' in df.columns:
        top_category = (
            df.groupby('category')['total_amount']
            .sum()
            .idxmax()
        )

        insights.append(
            f"🏆 Highest Revenue Category: {top_category}"
        )

    if 'payment_type' in df.columns:
        top_payment = df['payment_type'].mode()[0]

        insights.append(
            f"💳 Most Used Payment Method: {top_payment}"
        )

    if 'delivery_days' in df.columns:
        avg_delivery = round(
            df['delivery_days'].mean(),
            2
        )

        insights.append(
            f"🚚 Average Delivery Time: {avg_delivery} days"
        )

    if 'total_amount' in df.columns:
        revenue = int(df['total_amount'].sum())

        insights.append(
            f"💰 Total Revenue: ₹{revenue:,}"
        )

    for insight in insights:
        st.success(insight)

st.markdown("---")

# ---------- Data and download ----------
st.subheader("Filtered Data (first 200 rows)")
st.dataframe(df.head(200))

csv_bytes = to_csv_bytes(df)
st.download_button("📥 Download filtered data (CSV)", csv_bytes, file_name="filtered_orders.csv", mime="text/csv")


st.sidebar.markdown("""
# ⚙ Analytics Controls
Upload Dataset & Apply Filters
""")
