
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(
    page_title="Kenya Crime Analyzer",
    layout="wide",
)

def load_data():
    df = pd.read_csv("kenya_county_crime.csv")
    df.columns = df.columns.str.strip()
    df["Severity"] = df["Crime_Type"].apply(check_severity)
    return df

def check_severity(crime):
    crime = str(crime).lower()
    violent = ["murder", "robbery", "gbv", "assault"]
    petty   = ["theft", "burglary", "pickpocketing", "fraud"]
    for c in violent:
        if c in crime:
            return "Violent"
    for c in petty:
        if c in crime:
            return "Petty"
    return "Other"

def get_zone(violent_cases, petty_cases):
    if violent_cases >= petty_cases and violent_cases > 0:
        return "RED ZONE", "#e74c3c"
    elif petty_cases > violent_cases:
        return "ORANGE ZONE", "#e67e22"
    return "UNKNOWN", "#95a5a6"

st.markdown("## Kenya County Crime Analyzer")
st.caption("Analyze crime patterns by county, ward, or crime type")
st.divider()

try:
    data = load_data()
except FileNotFoundError:
    st.error(
        "**`kenya_county_crime.csv` not found.**  \n"
        "Place the CSV file in the same folder as `app.py` and refresh."
    )
    st.stop()

with st.sidebar:
    st.header(" Search & Filter")

    search_mode = st.radio(
        "Search by",
        ["County / Ward", "Crime Type"],
        horizontal=False,
    )

    if search_mode == "County / Ward":
        counties = sorted(data["County"].dropna().unique())
        selected_county = st.selectbox("County", counties)

        wards = sorted(data[data["County"] == selected_county]["Ward"].dropna().unique())
        selected_ward = st.selectbox("Ward (optional — leave as 'All' for county view)", ["All"] + list(wards))

    else:
        crimes = sorted(data["Crime_Type"].dropna().unique())
        selected_crime = st.selectbox("Crime Type", crimes)
        top_n = st.slider("Show top N locations", 3, 15, 5)

    st.divider()
    st.markdown("**Dataset summary**")
    st.caption(f"{len(data):,} records · {data['County'].nunique()} counties · {data['Crime_Type'].nunique()} crime types")

if search_mode == "County / Ward":
    if selected_ward == "All":
        filtered = data[data["County"] == selected_county]
        scope_label = selected_county
    else:
        filtered = data[(data["County"] == selected_county) & (data["Ward"] == selected_ward)]
        scope_label = f"{selected_county} › {selected_ward}"

    severity_totals = filtered.groupby("Severity")["Cases"].sum()
    violent_cases   = int(severity_totals.get("Violent", 0))
    petty_cases     = int(severity_totals.get("Petty",   0))
    total_cases     = int(filtered["Cases"].sum())

    zone_label, zone_color = get_zone(violent_cases, petty_cases)

 
    st.markdown(f"### Results for **{scope_label}**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cases",    f"{total_cases:,}")
    c2.metric("Violent Cases",  f"{violent_cases:,}")
    c3.metric("Petty Cases",    f"{petty_cases:,}")
    with c4:
        st.markdown(
            f"<div style='background:{zone_color};color:#fff;padding:10px 14px;"
            f"border-radius:10px;text-align:center;font-weight:600;font-size:15px;"
            f"margin-top:4px'>{zone_label}</div>",
            unsafe_allow_html=True,)

    st.divider()

    col_left, col_right = st.columns(2)


    with col_left:
        st.markdown("#### Top crimes reported")
        top_crimes = (
            filtered.groupby("Crime_Type")["Cases"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        fig_bar = px.bar(
            top_crimes,
            x="Cases",
            y="Crime_Type",
            orientation="h",
            color="Cases",
            color_continuous_scale=["#f39c12", "#e74c3c"],
            labels={"Crime_Type": "", "Cases": "Cases"},
        )
        fig_bar.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#888",
        )
        st.plotly_chart(fig_bar, use_container_width=True)


    with col_right:
        st.markdown("#### Severity breakdown")
        sev_df = severity_totals.reset_index()
        sev_df.columns = ["Severity", "Cases"]
        color_map = {"Violent": "#e74c3c", "Petty": "#e67e22", "Other": "#95a5a6"}
        fig_pie = px.pie(
            sev_df,
            names="Severity",
            values="Cases",
            color="Severity",
            color_discrete_map=color_map,
            hole=0.45,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#888",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    
    if selected_ward == "All":
        st.divider()
        st.markdown("#### Ward-by-ward breakdown")
        ward_summary = (
            filtered.groupby("Ward")["Cases"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig_ward = px.bar(
            ward_summary,
            x="Ward",
            y="Cases",
            color="Cases",
            color_continuous_scale=["#f39c12", "#e74c3c"],
        )
        fig_ward.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#888",
            xaxis_title="",
        )
        st.plotly_chart(fig_ward, use_container_width=True)

  
    st.divider()
    with st.expander(" View raw data"):
        st.dataframe(
            filtered[["County", "Ward", "Crime_Type", "Cases", "Severity"]]
            .sort_values("Cases", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

else:
    crime_data = data[data["Crime_Type"].str.contains(selected_crime, case=False, na=False)]

    st.markdown(f"### Results for crime type: **{selected_crime}**")

    total = int(crime_data["Cases"].sum())
    counties_hit = crime_data["County"].nunique()
    wards_hit    = crime_data["Ward"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cases",       f"{total:,}")
    c2.metric("Counties Affected", counties_hit)
    c3.metric("Wards Affected",    wards_hit)

    st.divider()

    col_left, col_right = st.columns(2)

    
    with col_left:
        st.markdown(f"#### Top {top_n} locations")
        top_locs = (
            crime_data.groupby(["County", "Ward"])["Cases"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
        top_locs["Label"] = top_locs["County"] + " › " + top_locs["Ward"]

        
        def zone_tag(row):
            loc_data = data[(data["County"] == row["County"]) & (data["Ward"] == row["Ward"])]
            sev = loc_data.groupby("Severity")["Cases"].sum()
            z, _ = get_zone(int(sev.get("Violent", 0)), int(sev.get("Petty", 0)))
            return z

        top_locs["Zone"] = top_locs.apply(zone_tag, axis=1)
        color_map_zone   = {"RED ZONE": "#e74c3c", "ORANGE ZONE": "#e67e22", "UNKNOWN": "#95a5a6"}

        fig_loc = px.bar(
            top_locs,
            x="Cases",
            y="Label",
            orientation="h",
            color="Zone",
            color_discrete_map=color_map_zone,
            labels={"Label": "", "Cases": "Cases"},
        )
        fig_loc.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#888",
            legend_title_text="Zone",
        )
        st.plotly_chart(fig_loc, use_container_width=True)

    with col_right:
        st.markdown("#### Cases by county")
        county_dist = (
            crime_data.groupby("County")["Cases"]
            .sum()
            .reset_index()
        )
        fig_county = px.pie(
            county_dist,
            names="County",
            values="Cases",
            hole=0.45,
        )
        fig_county.update_traces(textinfo="percent+label")
        fig_county.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#888",
        )
        st.plotly_chart(fig_county, use_container_width=True)

    st.divider()
    with st.expander(" View raw data"):
        st.dataframe(
            crime_data[["County", "Ward", "Crime_Type", "Cases", "Severity"]]
            .sort_values("Cases", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

st.divider()
st.markdown("### Export")
dl1, dl2, *_ = st.columns(4)

csv_bytes = filtered.to_csv(index=False).encode() if search_mode == "County / Ward" else crime_data.to_csv(index=False).encode()
fname = scope_label.replace(" › ", "_") if search_mode == "County / Ward" else selected_crime.replace(" ", "_")

dl1.download_button(
    " Download CSV",
    data=csv_bytes,
    file_name=f"kenya_crime_{fname}.csv",
    mime="text/csv",
    use_container_width=True,
)
