import streamlit as st
import requests
import datetime
import altair as alt
import pandas as pd

# Get data from NY Times

# County data
counties_data_url = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv"
counties_df = pd.read_csv(counties_data_url)
counties_df['date'] = pd.to_datetime(counties_df['date'])
counties_df = counties_df[counties_df.county != 'Unknown']  # removing cases that have unknown counties
counties = sorted(list(set(counties_df['county'])))
states = sorted(list(set(counties_df['state'])))

# State data
states_data_url = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"
states_df = pd.read_csv(states_data_url)
states_df['date'] = pd.to_datetime(states_df['date'])

# Headings
st.header("Compare spread of Covid-19 among US counties")
st.markdown("""
    This is not meant to be a comprehensive dashboard. I made this because I wanted an easy way to compare
    how coronavirus has spread at a more granular level. Thankfully, New York Times is publishing 
    [county-level data] (https://github.com/nytimes/covid-19-data), which I use to build the visualisations below.
    \n\nFor comprehensive and high-level visualisations, check out [NY Times] (https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html) 
    and [John Hopkins] (https://coronavirus.jhu.edu/map.html).
""")
st.write('Data as of', max(counties_df['date']).strftime("%B %d, %Y"))

# Dataframe of counties with most cases

# Display data frame
st.subheader("Counties with most cases")
st.markdown("Filter states by selecting below. Clear options to see all states.")
options_states = st.multiselect("States", states, default=['California', 'New York', 'Washington'])


@st.cache
def format_display_data(counties_df, states):
    if len(options_states) == 0:
        disp_df = counties_df.groupby(['county', 'state'])['cases'].sum().reset_index()
    else:
        disp_df = counties_df[counties_df['state'].isin(states)].groupby(['county', 'state'])[
            'cases'].sum().reset_index()

    disp_df_2 = \
        counties_df[(counties_df['date'] > max(counties_df['date']) - datetime.timedelta(days=3))].groupby('county')[
            'cases'].sum().reset_index()
    disp_df = disp_df.merge(disp_df_2, on='county')
    old_cases = disp_df['cases_x'] - disp_df['cases_y']
    disp_df['perc_change'] = 100 * (disp_df['cases_x'] - old_cases) / old_cases
    disp_df.columns = ['County', 'State', 'Cases', 'Cases last 72h', '% change']
    disp_df = disp_df.sort_values(by='Cases', ascending=False)
    return disp_df


disp_df = format_display_data(counties_df, options_states)

st.dataframe(disp_df.style.highlight_max(axis=0), height=150)

# Widgets
st.subheader("Compare counties and states")
st.markdown("Add or remove counties and states below. There are additional options in the sidebar.")
options_counties = st.multiselect("Counties", counties,
                                  default=['San Francisco', 'Los Angeles'])
options_states = st.multiselect('States', states, default='California')

# Side bar options
start_date = st.sidebar.date_input('Start date', datetime.date(2020, 3, 1))

category = st.sidebar.radio("Category", ('Cases', 'Deaths'))


@st.cache
def format_plot_data(counties_df, counties, states_df, states):
    df = counties_df[
        (counties_df['county'].isin(counties))]  # Remove most recent date since some counties haven't updated yet
    df.rename(columns={"county": "geo"}, inplace=True)
    df.drop(columns=['state', 'fips'], inplace=True)
    df2 = states_df[(states_df['state'].isin(states))]
    df2.rename(columns={"state": "geo"}, inplace=True)
    df2.drop(columns=['fips'], inplace=True)
    df = df.append(df2, ignore_index=True)
    df['cases_cum_value'] = df.sort_values(['geo', 'date'], ascending=True).groupby('geo')['cases'].cumsum()
    df['deaths_cum_value'] = df.sort_values(['geo', 'date'], ascending=True).groupby('geo')['deaths'].cumsum()
    df = df[df['date'] > pd.to_datetime(start_date)]  # '2020-02-20']  # Remove early dates without much data
    return df


plot_df = format_plot_data(counties_df, options_counties, states_df, options_states)
if category == 'Cases':

    st.subheader("Cumulative cases")
    alt_lc = alt.Chart(plot_df).mark_line().encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('cases_cum_value', axis=alt.Axis(title='Count')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white'))
    )
    st.altair_chart(alt_lc, use_container_width=True)
else:

    st.subheader("Cumulative deaths")
    alt_lc = alt.Chart(plot_df).mark_line().encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('deaths_cum_value', axis=alt.Axis(title='Count')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white'))
    )
    st.altair_chart(alt_lc, use_container_width=True)

st.write("----------")
st.write("""
    By [Tony Liu] (https://tonydl.com/) | source: [GitHub] (https://github.com/tdliu/covid_19) | data source: [NY Times] (https://github.com/nytimes/covid-19-data)
""")
