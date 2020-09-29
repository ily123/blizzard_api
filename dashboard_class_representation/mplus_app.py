import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output

import figure


def load_data():
    """Loads spec data and pivots it."""
    df = pd.read_pickle("keynums_groupby_level_spec.pkl")
    table = pd.pivot_table(
        df, values="num_keys", index=["spec"], columns=["key_level"], fill_value=0
    )
    return table


def load_week_data():
    df = pd.read_pickle("top500_keynums_groupby_period_dungeon_spec.pkl")
    df = df[["period", "spec", "num_keys"]].groupby(by=["period", "spec"]).sum()
    df = df.reset_index()
    week_table = pd.pivot_table(
        df, values="num_keys", index="spec", columns="period", fill_value=0
    )
    return week_table


def generate_figure(data):
    """Constructs the spec figure."""
    ridgeplot = figure.RidgePlot(data)
    return ridgeplot.figure


def generate_stack_figure(data, chart_type, role):
    """Constructs stack area chart."""
    stac = figure.StackedAreaPlot(data, chart_type, role)
    stac_fig = stac.assemble_figure()
    return stac_fig


figure_list = html.Ul(
    children=[
        html.Li(
            html.A(
                "FIGURE 1: Overview of all keys completed this season", href="#figure1"
            )
        ),
        html.Li(html.A("FIGURE 2: Spec participation vs its peers.", href="#figure2")),
        html.Li(
            html.A(
                "FIGURE 3: Changes in top 500 representation week-to-week.",
                href="#figure3",
            )
        ),
    ]
)

role_options = [
    {"label": "TANK", "value": "tank"},
    {"label": "HEALER", "value": "healer"},
    {"label": "MELEE DPS", "value": "mdps"},
    {"label": "RANGE DPS", "value": "rdps"},
]
scratch = """

    **What each panel shows**:

    * Panel 1 gives you a quick birds-eye view at which specs are the most numerous,
    and which spec have the longest tails. (In technical parlance, Panel 1 is a
    'ridge plot'. It shows a histogram for each spec. Each histogram tells you how many
    runs (y axis) that spec has completed at a particular key level (x axis). Mouse over
    the ridge to see exact numbers!
    * Panel 2 is supplementary to panel 1, and gives a comparison of specs population
    regardless of key level. It's another way to look at total spec populations.
    * Panel 3 is also supplementary. It shows what is already apparent from Panel 1.
    """
figure1_explanation = dcc.Markdown(
    """
    We count all keys completed this season. Then, we break that number down
    by spec & key level (first panel), by spec alone (second panel), or just by key
    level (third panel).

    The figures are interactive, you can mouse over to see exact numbers,
    zoom in and out, and make box selections. To reset, click
    on the home icon in the right upper corner.


    **Key Insights**:
    * Population of the most-played specs often dwarves the least-played
    specs by 2 orders of magnitude (eg 100X).
    * The most played specs are usually also the most successful at cutting-edge M+.
    That's why they are played. Likewise, the least-played specs are also the worst
    performers.
    * While there are 4-5 really poor specs, most specs are within
    2-3 key levels of the cutting edge performers.
    * The main take-away for an ordinary player is that you should probably stay
    away from the bottom 4 to 5 specs, but should feel free to play anything else.

    **Interesting Tidbit**:

    One way to tell if a spec is truly dead is to compare the number of runs it has at
    key level +15 vs +2. If a spec has more runs at +2 than at +15, it means that it's
    only played by newbie characters. By the time these characters get to doing their
    weekly +15s, they switch out to something better. A spec like that is not played at
    end-game. Specs like this include XYZ. Meanwhile, there are low-population specs that are
    played at +15 (eg: feral druid, demo lock).
    """
)

figure2_explanation = dcc.Markdown(
    """
    In Figure 1 above, the number of runs in the high-end bracket is so low that it's
    hard to see differences between specs.

    To solve this problem, we normalize the run counts  to 100% within each key level.
    For example, there are a total of XYZ runs at level +15. Warriors make up XYZ runs
    (that's XYZ %), prot paladins are XYZx (ectr), an so on. Together all the tanks
    at +15 add up to 100% at level +15.
    We do this normaliztion for each key level, and show specs grouped with their peers
    only.

    **Key Insights:**

    * The meta starts kicking in at +16. That's when most specs begin
    losing their share of representation to the meta classes.
    * Some non-meta specs stay relatively stable (or even gain share) in mid-range keys
    (disc, brew, shadow, arms), and only begin losing representation at higher levels.
    Play these if you want to feel special, yet competitive :)
    """
)
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

data = load_data()
week_data = load_week_data()
fig = generate_figure(data)
fig2 = generate_stack_figure(data, "key", "mdps")
fig3 = generate_stack_figure(week_data, "week", "mdps")

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(
    children=[
        html.H1(children="I get declined from M+ LFG! What shoud I play?"),
        figure_list,
        html.A(id="figure1"),
        html.H4(children="Overview of all keys completed this season"),
        html.Div(figure1_explanation),
        dcc.Tabs(
            children=[
                dcc.Tab(
                    label="SPEC & KEY LEVEL",
                    children=[
                        dcc.Dropdown(
                            id="figure1-dropdown",
                            options=[
                                {"label": "SORT BY BEST KEY", "value": "key"},
                                {
                                    "label": "SORT BY TOTAL POPULATION",
                                    "value": "population",
                                },
                            ],
                            value="key",
                            clearable=False,
                        ),
                        dcc.Graph(id="example-graph", figure=fig),
                    ],
                ),
                dcc.Tab(label="SPEC", children=[]),
                dcc.Tab(label="KEY LEVEL", children=[]),
            ]
        ),
        html.H4(children="Detailed Look at Spec Performance"),
        html.Div(figure2_explanation),
        dcc.Dropdown(
            id="figure2-dropdown",
            options=role_options,
            value="tank",
            clearable=False,
        ),
        dcc.Graph(id="keylevel-stacked-fig", figure=fig2),
        html.Div("heyyyyyy"),
        dcc.Dropdown(
            id="figure3-dropdown",
            options=role_options,
            value="tank",
            clearable=False,
        ),
        dcc.Graph(id="week-stacked-fig", figure=fig3),
    ]
)


@app.callback(
    Output(component_id="example-graph", component_property="figure"),
    [Input(component_id="figure1-dropdown", component_property="value")],
)
def update_figure1(input_value):
    """Switch between sorted by key and sorted by population view."""
    if input_value == "key":
        return fig
    elif input_value == "population":
        return fig2
    return fig


@app.callback(
    Output(component_id="keylevel-stacked-fig", component_property="figure"),
    [Input(component_id="figure2-dropdown", component_property="value")],
)
def update_figure2(role):
    """Switch between sorted by key and sorted by population view."""
    stack_figure = generate_stack_figure(data=data, chart_type="key", role=role)
    return stack_figure


@app.callback(
    Output(component_id="week-stacked-fig", component_property="figure"),
    [Input(component_id="figure3-dropdown", component_property="value")],
)
def update_figure3(role):
    """Switch between sorted by key and sorted by population view."""
    stack_figure = generate_stack_figure(data=week_data, chart_type="week", role=role)
    return stack_figure


if __name__ == "__main__":
    app.run_server(debug=True)
