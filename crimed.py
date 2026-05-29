import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Kenya Crime Analyzer",
    layout="wide",
)

REPORTS_FILE = "crime_reports.json"

def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_reports(reports):
    with open(REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=2)

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

def is_murder(crime_type):
    return "murder" in str(crime_type).lower()

def check_duplicate_murder(reports, county, ward, gender, age):
    for r in reports:
        if (
            is_murder(r.get("crime_type", ""))
            and r.get("county", "").lower() == county.lower()
            and r.get("ward", "").lower() == ward.lower()
            and r.get("victim_gender", "").lower() == gender.lower()
            and str(r.get("victim_age", "")) == str(age)
        ):
            return True, r
    return False, None

st.markdown("## Kenya County Crime Analyzer")
st.caption("Analyze crime patterns by county, ward, or crime type")
st.divider()

try:
    data = load_data()
except FileNotFoundError:
    st.error(
        "**`kenya_county_crime.csv` not found.**  \n"
        "Place the CSV file in the same folder as `crime.py` and refresh."
    )
    st.stop()

reports = load_reports()

with st.sidebar:
    st.header("Search & Filter")

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
    if reports:
        st.caption(f"{len(reports)} user-submitted report(s)")

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_analyze, tab_report, tab_my_reports = st.tabs([
    "Analyze Crime Data",
    "Report a Crime",
    "Submitted Reports",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYZE
# ══════════════════════════════════════════════════════════════════════════════
with tab_analyze:
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

        # User reports for this scope
        scope_reports = [
            r for r in reports
            if r.get("county") == selected_county
            and (selected_ward == "All" or r.get("ward") == selected_ward)
        ]
        if scope_reports:
            st.info(f"**{len(scope_reports)}** community report(s) submitted for this area. See the 'Submitted Reports' tab.")

        st.markdown(f"### Results for **{scope_label}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Cases",   f"{total_cases:,}")
        c2.metric("Violent Cases", f"{violent_cases:,}")
        c3.metric("Petty Cases",   f"{petty_cases:,}")
        with c4:
            st.markdown(
                f"<div style='background:{zone_color};color:#fff;padding:10px 14px;"
                f"border-radius:10px;text-align:center;font-weight:600;font-size:15px;"
                f"margin-top:4px'>{zone_label}</div>",
                unsafe_allow_html=True,
            )

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
                top_crimes, x="Cases", y="Crime_Type", orientation="h",
                color="Cases", color_continuous_scale=["#f39c12", "#e74c3c"],
                labels={"Crime_Type": "", "Cases": "Cases"},
            )
            fig_bar.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#888",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.markdown("#### Severity breakdown")
            sev_df = severity_totals.reset_index()
            sev_df.columns = ["Severity", "Cases"]
            color_map = {"Violent": "#e74c3c", "Petty": "#e67e22", "Other": "#95a5a6"}
            fig_pie = px.pie(
                sev_df, names="Severity", values="Cases",
                color="Severity", color_discrete_map=color_map, hole=0.45,
            )
            fig_pie.update_traces(textinfo="percent+label")
            fig_pie.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#888",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        if selected_ward == "All":
            st.divider()
            st.markdown("#### Ward-by-ward breakdown")
            ward_summary = (
                filtered.groupby("Ward")["Cases"]
                .sum().sort_values(ascending=False).reset_index()
            )
            fig_ward = px.bar(
                ward_summary, x="Ward", y="Cases", color="Cases",
                color_continuous_scale=["#f39c12", "#e74c3c"],
            )
            fig_ward.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#888", xaxis_title="",
            )
            st.plotly_chart(fig_ward, use_container_width=True)

        st.divider()
        with st.expander("View raw data"):
            st.dataframe(
                filtered[["County", "Ward", "Crime_Type", "Cases", "Severity"]]
                .sort_values("Cases", ascending=False),
                use_container_width=True, hide_index=True,
            )

    else:
        crime_data = data[data["Crime_Type"].str.contains(selected_crime, case=False, na=False)]
        st.markdown(f"### Results for crime type: **{selected_crime}**")

        total        = int(crime_data["Cases"].sum())
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
                .sum().sort_values(ascending=False).head(top_n).reset_index()
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
                top_locs, x="Cases", y="Label", orientation="h",
                color="Zone", color_discrete_map=color_map_zone,
                labels={"Label": "", "Cases": "Cases"},
            )
            fig_loc.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#888", legend_title_text="Zone",
            )
            st.plotly_chart(fig_loc, use_container_width=True)

        with col_right:
            st.markdown("#### Cases by county")
            county_dist = crime_data.groupby("County")["Cases"].sum().reset_index()
            fig_county = px.pie(county_dist, names="County", values="Cases", hole=0.45)
            fig_county.update_traces(textinfo="percent+label")
            fig_county.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#888",
            )
            st.plotly_chart(fig_county, use_container_width=True)

        st.divider()
        with st.expander("View raw data"):
            st.dataframe(
                crime_data[["County", "Ward", "Crime_Type", "Cases", "Severity"]]
                .sort_values("Cases", ascending=False),
                use_container_width=True, hide_index=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — REPORT A CRIME
# ══════════════════════════════════════════════════════════════════════════════
with tab_report:
    st.markdown("### Report a crime you have encountered")
    st.caption("Your report helps build a more complete picture of crime in your community.")
    st.divider()

    all_counties = sorted(data["County"].dropna().unique())
    all_crimes   = sorted(data["Crime_Type"].dropna().unique()) + ["Other (describe below)"]

    col_a, col_b = st.columns(2)

    with col_a:
        r_county = st.selectbox("County where it occurred", all_counties, key="r_county")
        r_wards  = sorted(data[data["County"] == r_county]["Ward"].dropna().unique())
        r_ward   = st.selectbox("Ward where it occurred", r_wards, key="r_ward")
        r_date   = st.date_input("Date of incident", value=datetime.today(), key="r_date")

    with col_b:
        r_crime  = st.selectbox("Crime type", all_crimes, key="r_crime")
        if r_crime == "Other (describe below)":
            r_crime_custom = st.text_input("Describe the crime type", key="r_crime_custom")
        r_desc   = st.text_area("Brief description (optional)", height=100, key="r_desc")

    # ── Murder-specific fields ──────────────────────────────────────────────
    murder_selected = is_murder(r_crime)
    if murder_selected:
        st.divider()
        st.markdown("#### Murder — additional details required")
        st.caption(
            "To avoid logging the same murder twice, please provide the victim's details. "
            "If a matching record already exists in this ward it will not be saved again."
        )
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            victim_gender = st.selectbox("Victim gender", ["Male", "Female", "Other / Unknown"], key="v_gender")
        with col_m2:
            victim_age = st.number_input("Victim age (approximate)", min_value=0, max_value=120, step=1, key="v_age")

    st.divider()
    submitted = st.button("Submit report", type="primary", use_container_width=False)

    if submitted:
        final_crime = r_crime if r_crime != "Other (describe below)" else r_crime_custom.strip()

        if not final_crime:
            st.error("Please enter a crime type.")
        elif murder_selected:
            # Duplicate check
            duplicate, existing = check_duplicate_murder(
                reports, r_county, r_ward, victim_gender, victim_age
            )
            if duplicate:
                st.warning(
                    f"A murder with these victim details (**{victim_gender}, age {victim_age}**) "
                    f"has already been reported in **{r_county} › {r_ward}** "
                    f"(reported on {existing.get('reported_at', 'unknown date')}). "
                    "This report has **not** been saved to avoid duplication."
                )
            else:
                new_report = {
                    "county":         r_county,
                    "ward":           r_ward,
                    "crime_type":     final_crime,
                    "description":    r_desc,
                    "incident_date":  str(r_date),
                    "reported_at":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "victim_gender":  victim_gender,
                    "victim_age":     int(victim_age),
                }
                reports.append(new_report)
                save_reports(reports)
                st.success(
                    f"Murder report saved for **{r_county} › {r_ward}**. "
                    "Thank you for reporting."
                )
        else:
            new_report = {
                "county":        r_county,
                "ward":          r_ward,
                "crime_type":    final_crime,
                "description":   r_desc,
                "incident_date": str(r_date),
                "reported_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            reports.append(new_report)
            save_reports(reports)
            st.success(
                f"Report saved for **{r_county} › {r_ward}** — {final_crime}. "
                "Thank you for reporting."
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SUBMITTED REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_my_reports:
    st.markdown("### All submitted community reports")
    st.divider()

    if not reports:
        st.info("No community reports have been submitted yet.")
    else:
        # Summary metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total reports",    len(reports))
        m2.metric("Counties covered", len(set(r.get("county","") for r in reports)))
        murder_reports = [r for r in reports if is_murder(r.get("crime_type",""))]
        m3.metric("Murder reports",   len(murder_reports))

        st.divider()

        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            filter_county = st.selectbox(
                "Filter by county", ["All"] + sorted(set(r.get("county","") for r in reports)),
                key="f_county"
            )
        with fc2:
            filter_crime = st.selectbox(
                "Filter by crime type", ["All"] + sorted(set(r.get("crime_type","") for r in reports)),
                key="f_crime"
            )

        filtered_reports = reports
        if filter_county != "All":
            filtered_reports = [r for r in filtered_reports if r.get("county") == filter_county]
        if filter_crime != "All":
            filtered_reports = [r for r in filtered_reports if r.get("crime_type") == filter_crime]

        for r in reversed(filtered_reports):
            severity = check_severity(r.get("crime_type",""))
            badge_color = "#e74c3c" if severity == "Violent" else "#e67e22" if severity == "Petty" else "#95a5a6"

            with st.container():
                ca, cb = st.columns([3, 1])
                with ca:
                    st.markdown(
                        f"**{r.get('crime_type','Unknown')}** &nbsp;"
                        f"<span style='background:{badge_color};color:#fff;padding:2px 8px;"
                        f"border-radius:6px;font-size:12px'>{severity}</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"{r.get('county','')} › {r.get('ward','')} &nbsp;|&nbsp; "
                        f"{r.get('incident_date','')} &nbsp;|&nbsp; "
                        f"Submitted: {r.get('reported_at','')}"
                    )
                    if r.get("description"):
                        st.markdown(f"> {r['description']}")
                    if is_murder(r.get("crime_type","")):
                        st.markdown(
                            f"Victim: **{r.get('victim_gender','N/A')}**, age **{r.get('victim_age','N/A')}**"
                        )
                st.divider()

        # Export
        if filtered_reports:
            df_reports = pd.DataFrame(filtered_reports)
            st.download_button(
                "⬇ Download reports as CSV",
                data=df_reports.to_csv(index=False).encode(),
                file_name="community_crime_reports.csv",
                mime="text/csv",
            )

# ══════════════════════════════════════════════════════════════════════════════
# EXPORT (original)
# ══════════════════════════════════════════════════════════════════════════════
with tab_analyze:
    st.divider()
    st.markdown("### Export")
    dl1, dl2, *_ = st.columns(4)

    if search_mode == "County / Ward":
        csv_bytes = filtered.to_csv(index=False).encode()
        fname = scope_label.replace(" › ", "_")
    else:
        csv_bytes = crime_data.to_csv(index=False).encode()
        fname = selected_crime.replace(" ", "_")

    dl1.download_button(
        "⬇ Download CSV",
        data=csv_bytes,
        file_name=f"kenya_crime_{fname}.csv",
        mime="text/csv",
        use_container_width=True,
    )
