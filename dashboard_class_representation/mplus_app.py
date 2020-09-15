import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

import figure
import figure2

def load_data():
    """Loads spec data and pivots it."""
    df = pd.read_pickle('keynums_groupby_level_spec.pkl')
    table = pd.pivot_table(df,
        values='num_keys', index=['spec'],
        columns=['key_level'],
        fill_value=0)
    return table 

def generate_figure(data):
    """Constructs the spec figure."""
    ridgeplot = figure.RidgePlot(data)
    ridgeplot.generate_components()
    fig = ridgeplot.assemble_components()
    return fig

def generate_stack_figure(data, role):
    """Constructs stack area chart."""
    stac = figure2.StackedAreaPlot(data)
    stac.construct_components(spec_role = role)
    stac_fig = stac.assemble_figure()
    return stac_fig

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

data = load_data()
fig = generate_figure(data)
fig2 = generate_stack_figure(data, 'mdps')

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(children=[
    html.H1(children='I get declined from M+ LFG! What shoud I play?'),
    html.Div(children='''
        Short answer: play anything that's not arcane, sub, survival, or marks. Long answer:
    '''),
    
    html.Ul(children = 
        [
            html.Li(children = [html.A('FIGURE 1: ', href='#figure1'), 
            """Spec distribution vs key level. This figure gives you a high-level overview of which specs are the most played, and what the highest level of key each spec has completed (not timed - in future releases will change this to timed)."""]),
            html.Li('FIGURE 2: Role-specific representation normalized for each key level. This figure tells you how spec composition changes as you progress through the key levels.'),
            html.Li('FIGURE 3: Week-by-week spec repsentation in top 1000. HOW DID META EVOLVE OVER TIME??')
        ]
    ),
    
    html.A(id='figure1'),
    html.H4(children = 'HIGH-LEVEL OVERVIEW'),
    html.H4(children = 'sub-header'),
    html.P(children = 'To understand which specs are the most popular, we counted all runs from Blizzard\'s leaderboard API in S4. We counter the number of runs that each spec participated in, as well as noted the best key each spec completed. The specs can be arranged by best key completed (default view), or by the total amount of runs. The figure has basic interactivy. Try mousing over to see the exact numbers!'),
    dcc.Tabs(children = [
        dcc.Tab(label='SPEC & KEY LEVEL', children = [
            dcc.Dropdown(
                id = 'figure1-dropdown',
                options = [
                    {'label': 'BEST KEY', 'value': 'key'},
                    {'label': 'TOTAL POPULATION', 'value': 'population'}
                ],
                value = 'key',
                clearable = False
                #placeholder = 'BEST KEY'
            ),
            dcc.Graph(
                id='example-graph',
                figure=fig
            )]),
        dcc.Tab(label = 'SPEC', children = []),
        dcc.Tab(label = 'KEY LEVEL', children = [])
    ]),
    html.H4(children = 'how to interpret'),
    html.P(children = 'The size of the colored area corresponds to the total number of runs a spec has. The size of the colored area gives you an intuitive visual perspective. For example, compare classes in the top 5 (havoc, BM, Resto, Prot War) to classes in the buttom 5 (sub, arcane, survival).'),
    html.P(children = 'The size of the colored area corresponds to the total number of runs a spec has. The size of the colored area gives you an intuitive visual perspective. For example, compare classes in the top 5 (havoc, BM, Resto, Prot War) to classes in the buttom 5 (sub, arcane, survival).'),
    dcc.Dropdown(
        id='figure2-dropdown',
        options = [
            {'label': 'TANK', 'value': 'tank'},
            {'label': 'HEALER', 'value': 'healer'},
            {'label': 'MELEE DPS', 'value': 'mdps'},
            {'label': 'RANGE DPS', 'value': 'rdps'}
        ],
        value = 'tank',
        clearable = False
    ),
    dcc.Graph(
        id='example-graph2',
        figure=fig2
    )
])

@app.callback(
    Output(component_id = 'example-graph', component_property = 'figure'),
    [Input(component_id = 'figure1-dropdown', component_property = 'value')]
)
def update_figure1(input_value):
    """Switch between sorted by key and sorted by population view."""
    if input_value == 'key':
        return fig
    elif input_value == 'population':
        return fig2
    return fig

@app.callback(
    Output(component_id = 'example-graph2', component_property = 'figure'),
    [Input(component_id = 'figure2-dropdown', component_property = 'value')]
)
def update_figure1(role):
    """Switch between sorted by key and sorted by population view."""
    stack_figure = generate_stack_figure(data, role)
    return stack_figure

if __name__ == '__main__':
    app.run_server(debug=True)
