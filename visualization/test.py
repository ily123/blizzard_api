import sqlite3

import pandas as pd
import plotly.express as px

import figure


def get_data_from_sqlite(db_file_path):
    """Get agg tables from the SQLite file."""
    conn = sqlite3.connect(db_file_path)
    main_summary = pd.read_sql_query("SELECT * FROM main_summary", conn)
    week_summary = pd.read_sql_query("SELECT * FROM weekly_summary", conn)
    conn.close()

    # pivot tables for the figure api
    main_summary = pd.pivot_table(
        main_summary,
        values="run_count",
        index=["spec"],
        columns=["level"],
        fill_value=0,
    )

    # oops, forgot to sum by dungeon before piping to SQLite, do it now:
    week_summary = (
        week_summary[["period", "spec", "run_count"]]
        .groupby(by=["period", "spec"])
        .sum()
    )
    week_summary = week_summary.reset_index()
    week_summary = pd.pivot_table(
        week_summary, values="run_count", index="spec", columns="period", fill_value=0
    )
    return main_summary, week_summary


def generate_ridgeplot(data):
    """Constructs the spec vs level ridge plot."""
    ridgeplot = figure.RidgePlot(data)
    return ridgeplot.figure


def generate_stack_figure(data, chart_type, role, stack_type):
    """Constructs stack area chart."""
    if stack_type == "area":
        stac = figure.StackedAreaChart(data, chart_type, role)
    elif stack_type == "bar":
        stac = figure.StackedBarChart(data, chart_type, role)
    stac_fig = stac.assemble_figure()
    return stac_fig


def generate_run_histogram(data):
    """Constructs keylevel vs run count histogram."""
    data = data.sum(axis=0)
    data = round(data / 5)  # there are 5 records per run
    data = data.astype(int)
    hist = figure.BasicHistogram(data)
    histfig = hist.make_figure()
    return histfig


def make_bubble_plot(data):
    """Construct spec run count bubble chart."""
    bubble = figure.BubblePlot(data)
    bubble_fig = bubble.make_figure2()
    return bubble_fig


# generate the figures
db_file_path = "../data/summary.sqlite"
main_summary, week_summary = get_data_from_sqlite(db_file_path)
ridgeplot_fig = generate_ridgeplot(main_summary)
bubble_fig = make_bubble_plot(main_summary)
histogram_fig = generate_run_histogram(main_summary)
stacked_levels_fig = generate_stack_figure(main_summary, "key", "mdps", "bar")
stacked_week_fig = generate_stack_figure(week_summary, "week", "mdps", "bar")
