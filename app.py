import streamlit as st
import requests
import datetime
import altair as alt
import pandas as pd

# Headings
st.header("Compare spread of Covid-19 among California counties")
st.markdown(
    "Data from SF Chronicle's [Coronavirus Tracker] (https://projects.sfchronicle.com/2020/coronavirus-map/).  \n\n"
    "This is *not* meant to be a comprehensive dashboard. SF Chronicle's tracker already has great data    for California. [NY Times] (https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html) and [John Hopkins] (https://coronavirus.jhu.edu/map.html) have comprehensive US and global visualisations. I made this because I wanted to compare how coronavirus has spread in San Francisco, where I live, with other regions.")

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
counties = sorted(list(set(data_pd['geography'])))
counties.remove('BAY AREA')
counties.remove('CALIFORNIA')

# Dataframe of counties with most cases
display_df = data_pd[data_pd['geography'].isin(counties)]
st.subheader("Counties with most cases")
display_df = display_df.groupby(['geography', 'category'])['value'].sum().reset_index()
display_df = display_df.pivot(index='geography', columns='category', values='value')

# Get cases in last 3 days
last_3_df = data_pd
last_3_df = last_3_df[
    (last_3_df['date'] > datetime.datetime.now() - datetime.timedelta(hours=72)) & (last_3_df['category'] == 'cases')]
last_3_df = last_3_df.groupby(['geography', 'category'])['value'].sum().reset_index()
last_3_df = last_3_df.pivot(index='geography', columns='category', values='value')

# Merge dataframes
display_df = display_df.merge(last_3_df, on='geography')
# Compute % change in cases
old_cases = display_df['cases_x'] - display_df['cases_y']
display_df['perc_change'] = 100 * (display_df['cases_x'] - old_cases) / old_cases
# Style dataframe
display_df.columns = ['Cases', 'Deaths', 'Cases last 72h', '% change']
display_df = display_df.sort_values(by='Cases', ascending=False)
st.dataframe(display_df.style.highlight_max(axis=0), height=150)

# Widgets
st.subheader("Compare counties")
st.markdown("Add or remove counties below. There are additional options in the sidebar.")
options_counties = st.multiselect("CA Counties (add or remove with selector below)", counties,
                                  default=['San Francisco County', 'Los Angeles County'])
geo_ms = st.sidebar.multiselect('Other regions:', ('CALIFORNIA', 'BAY AREA'), default='BAY AREA')
options_counties.extend(geo_ms)
start_date = st.sidebar.date_input('Start date', datetime.date(2020, 3, 1))
category_radio = st.sidebar.radio("Category", ('Cases', 'Deaths'))
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
    df = df[df['date'] > pd.to_datetime(start_date)]  # '2020-02-20']  # Remove early dates without much data
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
    color=alt.Color('geography', legend=alt.Legend(orient="top-left", fillColor='white'))
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
    color=alt.Color('geography', legend=alt.Legend(orient="top-left", fillColor='white'))
)
st.altair_chart(alt_lc, use_container_width=True)
