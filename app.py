import os
import time
import requests
import pandas as pd
import pytz
import streamlit as st

st.set_page_config(page_title="4S LiFePO₄ Monitor", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", "https://kxdrepyqiwleogzpxvtr.supabase.co"))
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4ZHJlcHlxaXdsZW9nenB4dnRyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUwMTAxNTAsImV4cCI6MjA3MDU4NjE1MH0.IMFZnjvWiT_wb4NlAOJHCKUj9HGF-_uXVHNz7nwo7oE"))
DEVICE_ID = os.getenv("DEVICE_ID", st.secrets.get("DEVICE_ID", "pack-4s2p-reza-s2mini"))
DEFAULT_TZ = os.getenv("LOCAL_TZ", st.secrets.get("LOCAL_TZ", "Asia/Jakarta"))

if not SUPABASE_URL:
    st.warning("Set SUPABASE_URL via environment or Streamlit secrets.")
if not SUPABASE_ANON_KEY:
    st.warning("Set SUPABASE_ANON_KEY via environment or Streamlit secrets.")

st.sidebar.header("Filters")
device_id = st.sidebar.text_input("Device ID", value=DEVICE_ID)
days = st.sidebar.slider("Days back", min_value=1, max_value=30, value=7)
limit = st.sidebar.slider("Max rows", min_value=500, max_value=20000, value=5000, step=500)
autorefresh = st.sidebar.checkbox("Auto-refresh", value=True)
interval = st.sidebar.slider("Refresh every (sec)", 5, 120, 15)
tz_name = st.sidebar.text_input("Local timezone (IANA)", value=DEFAULT_TZ)
status_filter = st.sidebar.multiselect("Status filter", ["green", "yellow", "red"], default=[])

@st.cache_data(ttl=60, show_spinner=False)
def fetch_cell_logs(url, api_key, device_id, days, limit):
    params = {
        "device_id": f"eq.{device_id}",
        "select": "*",
        "order": "ts.desc",
        "limit": str(limit),
    }
    import datetime as dt
    end = dt.datetime.utcnow().replace(microsecond=0)
    start = end - dt.timedelta(days=days)
    params["ts"] = f"gte.{start.isoformat()}Z"

    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    resp = requests.get(url.rstrip("/") + "/rest/v1/cell_logs", params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data)
    return df

def to_local(df, tzname):
    if df.empty: 
        return df
    tz = pytz.timezone(tzname)
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(tz)
    return df

st.title("🔋 4S LiFePO₄ Pack — Live Dashboard")

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        df = fetch_cell_logs(SUPABASE_URL, SUPABASE_ANON_KEY, device_id, days, limit)
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        df = pd.DataFrame()
else:
    df = pd.DataFrame()

if df.empty:
    st.info("No data yet. Verify RLS policy allows SELECT and the device is uploading.")
else:
    df = to_local(df, tz_name)
    df = df.sort_values("ts")

    if status_filter:
        df = df[df["status"].isin(status_filter)]

    latest = df.iloc[-1]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Pack V (latest)", f"{latest.get('pack_v', float('nan')):.3f} V")
    spread = latest.get("spread_mv", None)
    col2.metric("Spread (mV)", f"{int(spread) if pd.notna(spread) else 0}")
    col3.metric("Cell min (V)", f"{min(latest.get('c1',0),latest.get('c2',0),latest.get('c3',0),latest.get('c4',0)):.3f}")
    col4.metric("Cell max (V)", f"{max(latest.get('c1',0),latest.get('c2',0),latest.get('c3',0),latest.get('c4',0)):.3f}")
    col5.metric("Rows", f"{len(df)}")

    import altair as alt
    charts = []
    if "pack_v" in df:
        c_pack = alt.Chart(df).mark_line().encode(
            x="ts:T", y=alt.Y("pack_v:Q", title="Voltage (V)")
        ).properties(height=250)
        charts.append(c_pack)

    if all(col in df for col in ["c1","c2","c3","c4"]):
        df_cells = df.melt(id_vars=["ts"], value_vars=["c1","c2","c3","c4"], var_name="cell", value_name="voltage")
        c_cells = alt.Chart(df_cells).mark_line().encode(
            x="ts:T", y=alt.Y("voltage:Q", title="Voltage (V)"), color="cell:N"
        ).properties(height=250)
        charts.append(c_cells)

    if charts:
        st.altair_chart(alt.layer(*charts).resolve_scale(y='independent'), use_container_width=True)

    if "spread_mv" in df:
        st.subheader("Cell spread (mV)")
        c_spread = alt.Chart(df).mark_area(opacity=0.3).encode(
            x="ts:T", y=alt.Y("spread_mv:Q", title="mV")
        ).properties(height=150)
        st.altair_chart(c_spread, use_container_width=True)

    st.subheader("Recent rows")
    st.dataframe(df.tail(200).iloc[::-1], use_container_width=True, height=300)

if autorefresh:
    st.caption(f"Auto-refresh in {interval}s…")
    time.sleep(interval)
    st.rerun()
