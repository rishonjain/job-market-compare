"""Usage: uv run streamlit run app.py"""
import altair as alt
import duckdb
import streamlit as st

import db
from config import COUNTRIES

# Fixed role -> color (reference palette order); color follows the role, never its rank.
ROLES = {
    "Data Analyst": "#2a78d6", "Business Analyst": "#eb6834", "Analytics (other)": "#1baf7a",
    "Data Scientist": "#eda100", "Data Engineer": "#e87ba4", "ML Engineer": "#008300",
    "AI Engineer": "#6250d6", "Other": "#8a8985",
}
role_color = alt.Color("role:N", title="Role", sort=list(ROLES),
                       scale=alt.Scale(domain=list(ROLES), range=list(ROLES.values())))


@st.cache_data(ttl=600)
def load():
    # shortcut: read-only open fails while collect.py is writing; rerun the page after it finishes
    with duckdb.connect(str(db.DB_PATH), read_only=True) as con:
        df = con.execute("SELECT * EXCLUDE (description) FROM jobs").df()
    df["country_name"] = df["country"].map(COUNTRIES)
    return df


st.set_page_config(page_title="Data Jobs by Country", layout="wide")
st.title("Data jobs by country")

df = load()
names = sorted(df["country_name"].dropna().unique())
with st.sidebar:
    picked = st.multiselect("Countries", names, default=names[:3])
    roles = st.multiselect("Roles", list(ROLES)[:-1], default=list(ROLES)[:-1])
    if st.checkbox("Include unmatched titles (Other)"):
        roles.append("Other")
    st.caption(f"{len(df):,} unique jobs in database")

d = df[df["country_name"].isin(picked) & df["role"].isin(roles)]
if d.empty:
    st.info("Pick at least one country.")
    st.stop()

# --- Overview table
st.subheader("Overview")
overview = d.groupby("country_name").agg(
    jobs=("job_key", "size"), companies=("company", "nunique"), cities=("location", "nunique"),
    with_salary=("salary_min", lambda s: f"{s.notna().mean():.0%}"),
    sources=("source", "nunique"),
).sort_values("jobs", ascending=False)
st.dataframe(overview, width="stretch")

# --- Volume and role mix
c1, c2 = st.columns(2)
with c1:
    st.subheader("Jobs per country")
    st.altair_chart(alt.Chart(d).mark_bar(color="#2a78d6", cornerRadiusEnd=4).encode(
        y=alt.Y("country_name:N", sort="-x", title=None),
        x=alt.X("count():Q", title="Jobs"),
        tooltip=[alt.Tooltip("country_name:N", title="Country"), alt.Tooltip("count():Q", title="Jobs")],
    ), width="stretch")
with c2:
    st.subheader("Role mix")
    share = st.radio("Show", ["Share of country", "Count"], horizontal=True) == "Share of country"
    st.altair_chart(alt.Chart(d).mark_bar().encode(
        y=alt.Y("country_name:N", title=None),
        x=alt.X("count():Q", stack="normalize" if share else True,
                title="Share of jobs" if share else "Jobs", axis=alt.Axis(format="%" if share else "d")),
        color=role_color,
        order=alt.Order("role_order:Q"),
        tooltip=[alt.Tooltip("country_name:N", title="Country"), "role:N", alt.Tooltip("count():Q", title="Jobs")],
    ).transform_calculate(role_order=f"indexof({list(ROLES)}, datum.role)"), width="stretch")

# --- Data coverage: which sources feed each country (comparisons are only fair where coverage is similar)
st.subheader("Where the data comes from")
cov = d.groupby(["country_name", "source"]).size().reset_index(name="jobs")
st.altair_chart(alt.Chart(cov).mark_rect().encode(
    x=alt.X("country_name:N", title=None), y=alt.Y("source:N", title=None),
    color=alt.Color("jobs:Q", scale=alt.Scale(scheme="blues"), title="Jobs"),
    tooltip=["country_name:N", "source:N", "jobs:Q"],
) + alt.Chart(cov).mark_text(fontSize=11).encode(
    x="country_name:N", y="source:N", text="jobs:Q"), width="stretch")

# --- Per-country detail side by side
st.subheader("Top cities and employers")
for col, name in zip(st.columns(len(picked)), picked):
    c = d[d["country_name"] == name]
    with col:
        st.markdown(f"**{name}**")
        st.dataframe(c["location"].value_counts().head(10).rename("jobs"), width="stretch")
        st.dataframe(c["company"].value_counts().head(10).rename("jobs"), width="stretch")

# --- Browse
st.subheader("Browse postings")
q = st.text_input("Filter titles")
b = d[d["title"].str.contains(q, case=False, na=False)] if q else d
cols = ["country_name", "role", "title", "company", "location", "posted_at", "sources", "url"]
st.dataframe(b[cols].sort_values("posted_at", ascending=False), width="stretch", hide_index=True,
             column_config={"url": st.column_config.LinkColumn("Link")})
st.download_button("Download as CSV", b[cols].to_csv(index=False), "jobs.csv", "text/csv")
