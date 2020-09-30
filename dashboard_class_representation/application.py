import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output

import figure


def load_data():
    """Loads spec data and pivots it."""
    df = pd.read_pickle("keynums_groupby_level_spec2.pkl")
    table = pd.pivot_table(
        df, values="num_keys", index=["spec"], columns=["key_level"], fill_value=0
    )
    return table


def load_week_data():
    df = pd.read_pickle("top500_keynums_groupby_period_dungeon_spec2.pkl")
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


def generate_stack_figure(data, chart_type, role, stack_type):
    """Constructs stack area chart."""
    if stack_type == "area":
        stac = figure.StackedAreaChart(data, chart_type, role)
    elif stack_type == "bar":
        stac = figure.StackedBarChart(data, chart_type, role)
    stac_fig = stac.assemble_figure()
    return stac_fig


def generate_run_histogram():
    """Constructs keylevel vs run count histogram."""
    df = pd.read_pickle("keynums_groupby_level_spec.pkl")
    data = df[["key_level", "num_keys"]].groupby(by="key_level").sum()
    data = round(data / 5)  # there are 5 records per run
    data = data.astype(int)
    histchart = figure.BasicHistogram(data)
    histfig = histchart.make_figure()
    return histfig


def make_bubble_plot(data):
    """Construct spec run count bubble chart."""
    bubble = figure.BubblePlot(data)
    bubble_fig = bubble.make_figure2()
    return bubble_fig


figure_list = html.Ul(
    children=[
        html.Li(html.A("Overview of all keys completed this season", href="#figure1")),
        html.Li(html.A("Detailed Look at Spec Performance", href="#figure2")),
        html.Li(html.A("Weekly top 500", href="#figure3")),
        html.Li(html.A("FAQ", href="#faq")),
    ]
)

role_options = [
    {"label": "TANK", "value": "tank"},
    {"label": "HEALER", "value": "healer"},
    {"label": "MELEE DPS", "value": "mdps"},
    {"label": "RANGE DPS", "value": "rdps"},
]

radio_options = [
    {"label": "Bar Chart", "value": "bar"},
    {"label": "Area Chart", "value": "area"},
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


# html.H4(children=),
# html.Div(figure1_explanation),
def construct_figure_header(elements):
    """Constructs premade text elements that preceed figure."""
    children = [
        html.A(id=elements["anchor_id"]),
        html.H4(elements["header_title"].upper()),
        dcc.Markdown(elements["summary"]),
        html.Details(
            children=[html.Summary("Key Insights"), dcc.Markdown(elements["insight"])]
        ),
    ]
    if "factoid" in elements:
        children.append(
            html.Details(
                children=[
                    html.Summary("Interesting Factoid"),
                    dcc.Markdown(elements["factoid"]),
                ]
            )
        )
    return children


figure_header_elements = {
    "figure1": dict(
        anchor_id="figure1",
        header_title="Overview of all keys completed this season",
        summary="""
            We count all keys completed this season. Then, we break that number down
            by spec & key level (first panel), by spec alone (second panel),
            or just by key level (third panel).
            """,
        insight="""
            * Most specs are within 2-3 key levels of the cutting edge performers.
            Even the worst spec has done a +25.
            * Most specs that are popular with the general population
            are also the cutting-edge meta specs. It's likely that
            top-end meta propagates itself down to +15 level.
            * The bottom 4 to 6 specs are really in bad shape. No one plays them at
            any level of keystone. One exception are the Holy priests. They don't do
            well in high-end M+ but are played by the general population. They are a
            popular newbie healer spec for non-CE pushers.
            * The takeaway for ordinary players is that you should stay
            away from the very bottom specs, but feel free to play anything else.
            """,
        factoid="""
            * Once you get past +15, the number of key runs decays exponentially.
            Every two key levels, the number of runs drops by ~50%.
            So if you are doing +20 keys, you are already in the top 3%
            of the population.
            * One way to tell if a spec is truly dead is to compare the number of runs
            it has at key level +15 vs +2. If there are more runs at +2 than at +15,
            it means that the spec is only played by newbie characters.
            Once these characters get to weekly +15s, they switch specs.
            Most of the bottom 4-6 specs are like that. Meanwhile,
            there are low-population specs that do see more play at +15 than
            at +2 (eg: feral druid, frost dk, demo lock). These are specs that are
            played at end-game, even if not at cutting edge.
            """,
    ),
    "figure2": dict(
        anchor_id="figure2",
        header_title="Detailed Look at Spec Performance",
        summary="""
            The number of runs in the high-end bracket is so low,
            that it's hard to see difference between raw run counts in figure 1
            once you get past +20. To solve this problem, we normalize counts
            within each key bracket, and show spec popularity in terms of percent.

            Hint: Click on the spec names in the legend to add/remove them from the
            figure.
            """,
        insight="""
            * The meta starts kicking in at +16. That's where most specs begin to
            lose their share of representation to the meta classes.
            * Some non-meta specs stay relatively stable (or even gain share)
            in mid-range keys (disc, brew, shadow, arms), and only begin disappearing
            at higher levels.
            Play these if you want to feel special, yet somewhat competitive :)
            """,
    ),
    "figure3": dict(
        anchor_id="figure3",
        header_title="WEEKLY TOP 500",
        summary="""
            To see how the meta changes through the season, we sample the top 500 keys
            for each dungeon (that's 6000 total keys) for each week. We then count the
            number of times each spec appears in this weekly top 500 sample.

            Hint: Click on the spec names in the legend to add/remove them from the
            figure.
            """,
        insight="""
            * The meta is very stable within a single patch. Spec representation within
            top 500 rarely changes.
            * You do see *some* meta changes.
            Two examples this patch are the Balance Druids and Brewmaster Monks. Both
            started out this season strong, but faded away as time went by. These specs
            were popular in S3 for dealing with Beguiling, so there was carry-over at
            the start of S4 (additionally, monks were the default tanks for raid prog
            which probably boosted their repsentation in keys early this season).
            However, Balance was adjusted out of the meta completely by mid-season, and
            BrM fell from ~25% to ~10%.
            """,
        factoid="""
            If you notice, the data has a zig-zag quality to it.
            Spec numbers, especially the top spec, go up and down each week.
            That's the effect of the Tyranical/Fort split.
            On Tyrannical weeks, top pushers are likely to bench their meta-class mains
            and play non-meta alts (or not play at all).
            As a result on Tyrannical weeks, the share of the meta specs drops.
            Likewise, the share of meta specs rises to its max during push weeks
            (week 27 and 29 were the back to back push fort weeks, for example).

            Additionally, as we get closer to the end of the patch, many pushers
            stop playing, so we see non-meta specs gain some share past week 30.
            """,
    ),
}

errata_and_faq = dcc.Markdown(  # &nbsp; is a hacky way to add a blank line to MD
    """
    #### FAQ:

    **The top key this patch is a +32. Why do your charts only go up to +31?**

    The +32 was timed on the Chinese realms. My backend currently doesn't support CN.
    Support will be added in SL.

    &nbsp;

    **In your top figure why are you using completed key,
    instead of timed key, for BEST KEY?**

    It's not intended. I will add a timed/completed toggle in the future releases.

    &nbsp;

    **How frequently are the data updated?**

    Every 7 days on Tuesday. Daily updates coming soon (tm).

    &nbsp;

    **Why did you make this web site? Isn't raider.io enough?**

    Raider.io is great.
    For my part, I wanted a bit more insight into the data, so I made this dashboard.

    Other good M+ stats websites are [mplus.subcreation.net](mplus.subcreation.net)
    and [bestkeystone.com](bestkeystone.com).

    &nbsp;

    **Will you make more dashboards?**

    Yep. My goal is to add something new every 1 to 3 months.

    &nbsp;

    **I saw a mistake, have a comment, have an idea**

     My discord handle is []. Drop me a note whenever :)

    """
)


data = load_data()
week_data = load_week_data()
fig = generate_figure(data)
fig_bubble = make_bubble_plot(data)
fig_hist = generate_run_histogram()
fig2 = generate_stack_figure(data, "key", "mdps", "bar")
fig3 = generate_stack_figure(week_data, "week", "mdps", "bar")

app = dash.Dash(__name__)
application = app.server
app.title = "Benched: M+ Analytics"
app.layout = html.Div(
    html.Div(
        id="wrapper",
        children=[
            html.H1(children="Mythic+ at a glance"),
            figure_list,
            html.Div(
                className="figure-header",
                children=construct_figure_header(figure_header_elements["figure1"]),
            ),
            dcc.Tabs(
                children=[
                    dcc.Tab(
                        label="RUNS BY SPEC & KEY LEVEL",
                        children=[
                            dcc.Graph(
                                className="figure",
                                id="example-graph",
                                figure=fig,
                                config=dict(staticPlot=True),
                                # add margin here to compensate for title squish
                                style={"margin-top": "20px"},
                            )
                        ],
                    ),
                    dcc.Tab(
                        label="RUNS BY SPEC",
                        children=[
                            dcc.Graph(
                                className="figure",
                                id="fig1-bubble-chart",
                                figure=fig_bubble,
                            )
                        ],
                    ),
                    dcc.Tab(
                        label="RUNS BY KEY LEVEL",
                        children=[
                            dcc.Graph(
                                className="figure", id="fig1-key-hist", figure=fig_hist
                            )
                        ],
                    ),
                ]
            ),
            html.Hr(),
            html.Div(
                className="figure-header",
                children=construct_figure_header(figure_header_elements["figure2"]),
            ),
            dcc.RadioItems(
                id="figure2-radio",
                options=radio_options,
                value="bar",
            ),
            dcc.Dropdown(
                className="dropdown",
                id="figure2-dropdown",
                options=role_options,
                value="tank",
                clearable=False,
            ),
            dcc.Graph(id="keylevel-stacked-fig", figure=fig2),
            html.Hr(),
            html.Div(
                className="figure-header",
                children=construct_figure_header(figure_header_elements["figure3"]),
            ),
            dcc.RadioItems(
                id="figure3-radio",
                options=radio_options,
                value="bar",
            ),
            dcc.Dropdown(
                className="dropdown",
                id="figure3-dropdown",
                options=role_options,
                placeholder="SELECT SPEC ROLE",
                value="tank",
                clearable=False,
            ),
            dcc.Graph(id="week-stacked-fig", figure=fig3),
            html.Hr(),
            html.Div(id="faq", children=errata_and_faq),
        ],
    )
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
    [
        Input(component_id="figure2-dropdown", component_property="value"),
        Input(component_id="figure2-radio", component_property="value"),
    ],
)
def update_figure2(role, isbar):
    """Switch between sorted by key and sorted by population view."""
    print(role)
    print(isbar)
    print("=" * 80)
    stack_figure = generate_stack_figure(
        data=data, chart_type="key", role=role, stack_type=isbar
    )
    return stack_figure


@app.callback(
    Output(component_id="week-stacked-fig", component_property="figure"),
    [
        Input(component_id="figure3-dropdown", component_property="value"),
        Input(component_id="figure3-radio", component_property="value"),
    ],
)
def update_figure3(role, isbar):
    """Switch between sorted by key and sorted by population view."""
    stack_figure = generate_stack_figure(
        data=week_data, chart_type="week", role=role, stack_type=isbar
    )
    return stack_figure


if __name__ == "__main__":
    application.run(debug=True, port=8080)
