import streamlit as st
import datetime
import altair as alt
import pandas as pd

# Get data from NY Times

# County data
counties_data_url = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv"
counties_df = pd.read_csv(counties_data_url)
counties_df['date'] = pd.to_datetime(counties_df['date'])
counties_df = counties_df[counties_df.county != 'Unknown']  # removing cases that have unknown counties
counties_df['county_state'] = counties_df['county'] + ', ' + counties_df['state']
counties = sorted(list(set(counties_df['county_state'])))
states = sorted(list(set(counties_df['state'])))
curr_date = max(counties_df['date'])

# State data
states_data_url = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"
states_df = pd.read_csv(states_data_url)
states_df['date'] = pd.to_datetime(states_df['date'])

# Headings
st.header("Compare spread of Covid-19 among US counties")
st.markdown("""
    This is not meant to be a comprehensive dashboard. I made this because I wanted an easy way to compare
    how coronavirus has spread at a more granular level. Thankfully, The New York Times is publishing 
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
        disp_df = counties_df
    else:
        disp_df = counties_df[counties_df['state'].isin(states)]
    disp_df = disp_df[disp_df['date'] == curr_date]
    disp_df2 = counties_df[(counties_df['date'] == max(counties_df['date']) - datetime.timedelta(days=1))]
    disp_df = disp_df.merge(disp_df2[['county_state', 'cases', 'deaths']], on='county_state')
    disp_df['cases_last_day'] = disp_df['cases_x'] - disp_df['cases_y']
    disp_df['delta'] = 100 * (disp_df['cases_x'] - disp_df['cases_y']) / disp_df['cases_y']
    disp_df = disp_df[['county_state', 'cases_x', 'cases_last_day', 'delta']]
    disp_df.columns = ['County', 'Total cases', 'New cases', '% change']
    disp_df = disp_df.sort_values(by='New cases', ascending=False).reset_index(drop=True)
    return disp_df


disp_df = format_display_data(counties_df, options_states)

st.dataframe(disp_df.style.highlight_max(axis=0), height=275)

# Widgets
st.subheader("Compare counties and states")
st.markdown("Add or remove counties and states below.")

plot_counties = st.multiselect("Counties", counties,
                               default=['San Francisco, California', 'Los Angeles, California'])
plot_states = st.multiselect('States', states, default=['California', 'Washington'])
start_date = st.date_input('Start date', datetime.date(2020, 3, 10))
category = st.radio("Category", ('Cases', 'Deaths'))

def compute_growth_rate(delta, curr_total):
    return 100 * (curr_total - (curr_total - delta)) / (curr_total - delta)


# @st.cache
def format_plot_data(counties_df, counties, states_df, states):
    df = counties_df[counties_df['county_state'].isin(counties)]
    df.rename(columns={"county_state": "geo"}, inplace=True)
    df.drop(columns=['state', 'fips'], inplace=True)
    df2 = states_df[(states_df['state'].isin(states))]
    df2.rename(columns={"state": "geo"}, inplace=True)
    df2.drop(columns=['fips'], inplace=True)
    df = df.append(df2, ignore_index=True)
    df['previous_date'] = df['date'] - datetime.timedelta(days=1)
    df = pd.merge(df, df, left_on=['previous_date', 'geo'], right_on=['date', 'geo'])
    df['new_cases'] = df['cases_x'] - df['cases_y']
    df['new_deaths'] = df['deaths_x'] - df['deaths_y']
    df = df[['date_x', 'geo', 'cases_x', 'deaths_x', 'new_cases', 'new_deaths']]
    df.columns = ['date', 'geo', 'total_cases', 'total_deaths', 'new_cases', 'new_deaths']
    df['perc_daily_change_cases'] = 100 * df['new_cases'] / df['total_cases']
    df['perc_daily_change_deaths'] = 100 * df['new_deaths'] / df['total_deaths']
    df['avg_daily_change_rolling_7_cases'] = df.groupby('geo')['perc_daily_change_cases'].rolling(7).mean().reset_index(
        level=0, drop=True)
    df['avg_daily_change_rolling_7_deaths'] = df.groupby('geo')['perc_daily_change_deaths'].rolling(
        7).mean().reset_index(level=0, drop=True)
    df = df[df['date'] >= pd.to_datetime(start_date)]
    return df


ny_times_quote = """
    [The New York Times] (https://www.nytimes.com/interactive/2020/03/27/upshot/coronavirus-new-york-comparison.html): 
    >To assess the possible future of the outbreak, it’s helpful to look not just at 
    >the number of cases but also at how quickly they are increasing. The accompanying chart 
    >shows the growth rate of cumulative cases over time, averaged over the previous week."
    """

plot_df = format_plot_data(counties_df, plot_counties, states_df, plot_states)
if category == 'Cases':
    st.subheader("New cases")
    alt_lc = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('new_cases', axis=alt.Axis(title='Count')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=['geo', 'date', 'new_cases']
    )
    st.altair_chart(alt_lc, use_container_width=True)

    st.subheader("Total cases")
    alt_lc = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('total_cases', axis=alt.Axis(title='Count')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=['geo', 'date', 'total_cases']
    )
    st.altair_chart(alt_lc, use_container_width=True)
    st.markdown(ny_times_quote)
    st.subheader("Average daily change in total cases, over previous 7 days")
    alt_lc = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('avg_daily_change_rolling_7_cases', axis=alt.Axis(title='%')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=['geo', 'date', 'avg_daily_change_rolling_7_cases']
    )
    st.altair_chart(alt_lc, use_container_width=True)
else:
    st.subheader("New deaths")
    alt_lc = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('new_deaths', axis=alt.Axis(title='Count')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=['geo', 'date', 'new_deaths']
    )
    st.altair_chart(alt_lc, use_container_width=True)

    st.subheader("Total deaths")
    alt_lc = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('total_deaths', axis=alt.Axis(title='Count')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=['geo', 'date', 'total_deaths']
    )
    st.altair_chart(alt_lc, use_container_width=True)
    st.markdown(ny_times_quote)
    st.subheader("Average daily change in total deaths, over previous 7 days")
    alt_lc = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Date')),
        y=alt.Y('avg_daily_change_rolling_7_deaths', axis=alt.Axis(title='%')),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=['geo', 'date', 'avg_daily_change_rolling_7_deaths']
    )
    st.altair_chart(alt_lc, use_container_width=True)

st.write("----------")
st.write("""
    By [Tony Liu] (https://tonydl.com/) | source: [GitHub] (https://github.com/tdliu/covid_19) | data source: [NY Times] (https://github.com/nytimes/covid-19-data)
""")
