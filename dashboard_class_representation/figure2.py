"""Create stacked area chart from spec representation data."""

import importlib

import plotly.graph_objects as go

import blizzcolors

importlib.reload(blizzcolors)


class StackedAreaPlot(object):
    """Docstring."""

    def __init__(self, data, spec_role):
        """Inits with pivoted table of specs vs key levels."""
        self.data = data
        self.specs = blizzcolors.Specs()
        self.traces = self.construct_components(spec_role)

    def construct_components(self, spec_role):
        """Constructs figure components."""
        spec_ids = self.specs.get_spec_ids_for_role(spec_role)
        traces = self.make_trace(spec_ids)
        return traces

    def assemble_figure(self):
        """Assemble plotly figure from pre-made components."""
        fig = go.Figure(data=self.traces)
        return fig

    def make_trace(self, spec_ids):
        """Crates a trace dict for a spec."""
        valid_roles = ['tank', 'healer', 'mdps', 'rdps']
        keep_role = 'tank'
        keep_role = keep_role.lower()
        if keep_role not in valid_roles:
            raise ValueError('Spec role invalid. Must be one of: %s')

        traces = []
        for spec_id in spec_ids:
            key_level = list(self.data)
            spec_share = list(
                self.data.loc[self.data.index == spec_id, :].values[0])
            spec_color = 'rgba(%d,%d,%d,0.7)' % self.specs.get_color(spec_id)
            spec_trace = self.make_tracex(
                key_level, spec_share, fillcolor=spec_color)
            traces.append(spec_trace)
        return traces

    @staticmethod
    def make_tracex(key_level, spec_share, fillcolor):
        """Make trace dict for line."""
        trace = go.Scatter(
            x=key_level,
            y=spec_share,
            mode='lines',
            line=dict(width=1.5, color='black'),
            fillcolor=fillcolor,
            stackgroup='one',
            groupnorm='percent')
        return trace
