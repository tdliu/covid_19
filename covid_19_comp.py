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
counties_df.drop(columns=['fips'], inplace=True)
counties = sorted(list(set(counties_df['county_state'])))
states = sorted(list(set(counties_df['state'])))
curr_date = max(counties_df['date'])

# State data
states_data_url = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"
states_df = pd.read_csv(states_data_url)
states_df['date'] = pd.to_datetime(states_df['date'])
states_df.drop(columns=['fips'], inplace=True)

# Get data from CSSEGISandData
# Cases
global_data_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
global_df = pd.read_csv(global_data_url)
global_df.drop(['Province/State', 'Lat', 'Long'], inplace=True, axis=1)
# Sum by country
global_df = global_df.groupby('Country/Region').sum().reset_index()
global_df = pd.melt(global_df, id_vars=['Country/Region'], value_vars=global_df.columns[1:])
global_df.columns = ['country', 'date', 'cases']
# Fix Taiwan bug
global_df['country'].replace("Taiwan*", 'Taiwan', inplace=True)

# Deaths
global_data_url2 = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
global_df2 = pd.read_csv(global_data_url2)
global_df2.drop(['Province/State', 'Lat', 'Long'], inplace=True, axis=1)
# Sum by country
global_df2 = global_df2.groupby('Country/Region').sum().reset_index()
global_df2 = pd.melt(global_df2, id_vars=['Country/Region'], value_vars=global_df2.columns[1:])
global_df2.columns = ['country', 'date', 'deaths']
# Fix Taiwan bug
global_df2['country'].replace("Taiwan*", 'Taiwan', inplace=True)

global_df = global_df.merge(global_df2, on=['country', 'date'])
global_df['date'] = pd.to_datetime(global_df['date'])
countries = sorted(list(set(global_df['country'])))

# Headings
st.header("Compare spread of Covid-19")
st.subheader("Among US counties, US states, and countries")
st.markdown("""
    This is not meant to be a comprehensive dashboard. I made this because I wanted an easy way to compare
    how coronavirus has spread at a more granular level. Thankfully, The New York Times is publishing 
    [county-level data] (https://github.com/nytimes/covid-19-data), which I use to build the visualisations below.
    \n\nFor comprehensive and high-level visualisations, check out [NY Times] (https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html) 
    and [John Hopkins] (https://coronavirus.jhu.edu/map.html).
""")
st.write('County and state-level data from The New York Times updated up to',
         max(counties_df['date']).strftime("%B %d, %Y"),
         '.  \nCountry-level data from [John Hopkins CSSE] (https://github.com/CSSEGISandData/COVID-19) updated up to',
         max(global_df['date']).strftime("%B %d, %Y"), '.')

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
    disp_df.columns = ['County', 'Total cases', 'New cases', '% change last day']
    disp_df = disp_df.sort_values(by='New cases', ascending=False).reset_index(drop=True)
    return disp_df


disp_df = format_display_data(counties_df, options_states).set_index('County', drop=True)

st.dataframe(disp_df.style.highlight_max(axis=0), height=275)

# Widgets
st.subheader("Compare counties with states and other countries")
st.markdown("Add or remove counties and states below.")

plot_counties = st.multiselect("Counties", counties,
                               default=['San Francisco, California', 'Los Angeles, California'])
plot_states = st.multiselect('States', states, default=['California', 'Washington'])

# set defaults
start_date = datetime.date(2020, 3, 10)
category = 'Cases'
plot_countries = []
is_log = False
if st.checkbox('Check for more options, e.g. countries, date, cases/deaths.'):
    plot_countries = st.multiselect('Countries', countries)
    start_date = st.date_input('Start date', datetime.date(2020, 3, 10))
    category = st.radio("Category", ('Cases', 'Deaths'))


@st.cache
def format_plot_data(counties_df, counties, states_df, states, global_df, countries):
    df = counties_df[counties_df['county_state'].isin(counties)]
    df.rename(columns={"county_state": "geo"}, inplace=True)
    df.drop(columns=['state'], inplace=True)

    df2 = states_df[(states_df['state'].isin(states))]
    df2.rename(columns={"state": "geo"}, inplace=True)
    df = df.append(df2, ignore_index=True)

    df3 = global_df[(global_df['country'].isin(countries))]
    df3.rename(columns={"country": "geo"}, inplace=True)
    df = df.append(df3, ignore_index=True)

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
    [The New York Times] (https://www.nytimes.com/interactive/2020/03/21/upshot/coronavirus-deaths-by-country.html): 
    >Another way of looking at the same information is to plot the growth rates directly. With 
    >epidemics, these rates are often more important than the current totals. **A reading of 40 
    >percent on the chart below means that, on average, the number of deaths has been increasing 
    >by 40 percent each day.** A reading of 100 percent would mean that cases were doubling daily.    
    
    The accompanying chart shows the growth rate of cumulative cases over time, averaged over the 
    previous week.
    """

days_since_text = """
    [The New York Times] (https://www.nytimes.com/interactive/2020/03/21/upshot/coronavirus-deaths-by-country.html):
    >The accompanying chart... allows you to follow the disease’s 
    >progression by country. **It uses what’s called a logarithmic scale — exponential growth at 
    >different rates will appear as straight lines of different steepness.** The steeper the line, 
    >the higher the growth rate and the faster the total number of coronavirus deaths is doubling.
"""

plot_df = format_plot_data(counties_df, plot_counties, states_df, plot_states, global_df, plot_countries)
norm_date_df = plot_df[plot_df['total_cases'] > 50]
norm_date_df['days_since_50_cases'] = norm_date_df.groupby("geo")['date'].rank("min") - 1


def plot_line_chart(title, df, x, x_title, y, y_title, tooltip, scale='linear'):
    st.subheader(title)
    alt_lc = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X(x, axis=alt.Axis(title=x_title)),
        y=alt.Y(y, axis=alt.Axis(title=y_title), scale=alt.Scale(type=scale)),
        color=alt.Color('geo', legend=alt.Legend(orient="top-left", fillColor='white')),
        tooltip=tooltip
    )
    st.altair_chart(alt_lc, use_container_width=True)
    return


if category == 'Cases':
    # Plot new cases
    plot_line_chart(
        "New cases", plot_df, 'date', 'Date', 'new_cases', 'Count', ['geo', 'date', 'new_cases']
    )

    # Plot total cases
    plot_line_chart(
        "Total cases", plot_df, 'date', 'Date', 'total_cases', 'Count', ['geo', 'date', 'new_cases']
    )

    st.markdown(days_since_text)
    if st.checkbox('Log scale', value=True):
        scale = 'symlog'
    else:
        scale = 'linear'

    # Plot growth rate, timeline normalised
    plot_line_chart(
        "Total cases for regions with more than 50 cases", norm_date_df, 'days_since_50_cases',
        'Days since 50 cases', 'total_cases', 'Count',
        ['geo', 'date', 'days_since_50_cases', 'total_cases'], scale
    )
    # Plot growth rate, avg % daily change
    st.markdown(ny_times_quote)
    plot_line_chart(
        "Average daily change in total cases, over previous 7 days", plot_df, 'date', 'Date',
        'avg_daily_change_rolling_7_cases', '%', ['geo', 'date', 'avg_daily_change_rolling_7_cases']
    )
else:
    # Plot new deaths
    plot_line_chart(
        "New deaths", plot_df, 'date', 'Date', 'new_deaths', 'Count', ['geo', 'date', 'new_deaths']
    )

    # Plot total deaths
    plot_line_chart(
        "Total deaths", plot_df, 'date', 'Date', 'total_deaths', 'Count', ['geo', 'date', 'new_deaths']
    )

    st.markdown(days_since_text)
    if st.checkbox('Log scale', value=True):
        scale = 'symlog'
    else:
        scale = 'linear'
    # Plot growth rate, timeline normalised
    plot_line_chart(
        "Total deaths for regions with more than 50 cases", norm_date_df, 'days_since_50_cases',
        'Days since 50 cases', 'total_deaths', 'Count',
        ['geo', 'date', 'days_since_50_cases', 'total_deaths'], scale
    )
    # Plot growth rate, avg % daily change
    st.markdown(ny_times_quote)
    plot_line_chart(
        "Average daily change in total deaths, over previous 7 days", plot_df, 'date', 'Date',
        'avg_daily_change_rolling_7_deaths', '%', ['geo', 'date', 'avg_daily_change_rolling_7_deaths']
    )

st.write("----------")
st.write("""
    By [Tony Liu] (https://tonydl.com/) | source: [GitHub] (https://github.com/tdliu/covid_19) | 
    data source: [NY Times] (https://github.com/nytimes/covid-19-data), [John Hopkins CSSE] (https://github.com/CSSEGISandData/COVID-19)
""")
