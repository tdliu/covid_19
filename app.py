import streamlit as st
import requests
import datetime
import altair as alt
import pandas as pd

# Headings
st.header("Compare spread of Covid-19 among California counties")
st.markdown("Data from SF Chronicle's [Coronavirus Tracker] (https://projects.sfchronicle.com/2020/coronavirus-map/).  \n\n"
            "This is not meant to be a comprehensive dashboard. SF Chronicle's tracker already has great data    for California. [NY Times] (https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html) and [John Hopkins] (https://coronavirus.jhu.edu/map.html) have comprehensive US and global visualisations. I made this because I wanted to compare how coronavirus has spread in San Francisco, where I live, with other regions.")

# Get data
response = requests.get('https://files.sfchronicle.com/project-feeds/covid19_us_cases_ca_by_county_.json')
raw_data = response.json()
clean_data = []
for x in raw_data:
    county = x['GEOGRAPHY']
    category = x['CATEGORY']
    for key in x.keys():
        try:
            date = datetime.datetime.strptime(key, "%m/%d/%y")
            clean_data.append([county, category, date, int(x[key])])
        except ValueError:
            pass
data_pd = pd.DataFrame(clean_data, columns=['geography', 'category', 'date', 'value'])

# Widgets

counties = sorted(list(set(data_pd['geography'])))
counties.remove('BAY AREA')
counties.remove('CALIFORNIA')

options_counties = st.multiselect("CA Counties", counties, default=['San Francisco County', 'Los Angeles County'])
geo_ms = st.multiselect('Other regions:', ('CALIFORNIA', 'BAY AREA'), default = 'BAY AREA')
options_counties.extend(geo_ms)
category_radio = st.radio("Category", ('Cases', 'Deaths'))
if category_radio == 'Cases':
    category = 'cases'
else:
    category = 'deaths'


# Create dataframe
def format_plot_data(raw_df, geos, category='cases'):
    df = raw_df[(raw_df['category'] == category) &
                (raw_df['geography'].isin(geos)) &
                (raw_df['date'] <= max(
                    raw_df['date']))]  # Remove most recent date since some counties haven't updated yet
    df['cum_value'] = df.sort_values(['geography', 'date'], ascending=True).groupby('geography')['value'].cumsum()
    df = df[df['date'] > '2020-02-20']  # Remove early dates without much data
    return df


filtered_df = format_plot_data(data_pd, options_counties, category)

# Plot charts

# plot new cases
if category == 'cases':
    st.subheader("New cases")
else:
    st.subheader("New deaths")
alt_lc = alt.Chart(filtered_df).mark_line().encode(
    x=alt.X('date', axis=alt.Axis(title='Date')),
    y=alt.Y('value', axis=alt.Axis(title='Count')),
    color='geography'
)
st.altair_chart(alt_lc, use_container_width=True)

# plot cumulative cases
if category == 'cases':
    st.subheader("Cumulative cases")
else:
    st.subheader("Cumulative deaths")

alt_lc = alt.Chart(filtered_df).mark_line().encode(
    x=alt.X('date', axis=alt.Axis(title='Date')),
    y=alt.Y('cum_value', axis=alt.Axis(title='Count')),
    color='geography'
)
st.altair_chart(alt_lc, use_container_width=True)
