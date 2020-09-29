import importlib
from typing import Tuple, Type  # you have to import Type

import pandas as pd
import plotly.graph_objects as go

import blizzcolors


class StackedChart:

    hovertemplate = {
        "area+key": "KEY LEVEL: +%{x:d}<br> SHARE: %{y:.0f}%",
        "area+week": "WEEK: %{x}<br> SHARE: %{y:.0f}%",
        "bar+key": "%{text}<br>KEY LEVEL: %{x}<br> SHARE: %{y:.0f}%<extra></extra>",
        "bar+week": "%{text}<br>WEEK: %{x}<br> SHARE: %{y:.0f}%<extra></extra>",
    }

    def __init__(self, data, xaxis_type, spec_role):
        self.specs = blizzcolors.Specs()
        self.xaxis_type = xaxis_type
        self.spec_role = spec_role
        self.data = self.normalize_for_role(data, spec_role)
        self.traces = None

    def normalize_for_role(self, data, spec_role):
        # normalize data to 100% in each x bin
        spec_ids = self.specs.get_spec_ids_for_role(spec_role)
        data = data.loc[spec_ids, :]
        data = 100 * data / data.sum(axis=0)
        # adjust x axis to start with 1 for weekly charts
        if self.xaxis_type == "week":
            data.columns = data.columns - min(data.columns) + 1
        return data

    def get_xaxis(self) -> dict:
        """Creates plotly xaxis for the figure."""
        # add 0.5 padding to xrange for bar plots
        # otherwise, the bars are clipped by the axis box
        min_x = min(list(self.data))
        max_x = max(list(self.data))
        padding = self.get_padding_for_bar()
        range_ = (min_x - padding, max_x + padding)
        if self.xaxis_type == "key":
            tickvals = list(range(0, max_x + 1, 5))
            tickvals[0] = 2
            xaxis = dict(
                title="<b>KEY LEVEL</b>",
                range=range_,
                tickvals=tickvals,
                ticktext=["+" + str(tv) for tv in tickvals],
            )
        elif self.xaxis_type == "week":
            if max_x > 11:
                tickvals = list(range(0, max_x + 1, 4))
                tickvals[0] = 1
            else:
                tickvals = list(range(1, max_x + 1, 1))
            xaxis = dict(
                title="<b>WEEK</b>",
                range=range_,
                tickvals=tickvals,
                ticktext=[str(tv - min_x + 1) for tv in tickvals],
            )
        return xaxis

    def get_padding_for_bar(self):
        """Sets axis limit padding for bar plots."""
        padding = 0
        if isinstance(self.traces[0], go.Bar):
            padding = 0.5
        return padding

    @staticmethod
    def get_yaxis() -> dict:
        """Sets yaxis properties of a %normalized share-of-total figure."""
        ytickvals = [0, 20, 40, 60, 80, 100]
        yaxis = dict(
            title="<b>SHARE OF TOTAL (%)</b>",
            range=[0, 101],
            tickvals=ytickvals,
            ticktext=[str(val) + "%" for val in ytickvals],
        )
        return yaxis

    def assemble_figure(self):
        """Assemble plotly figure from pre-made components."""
        fig = go.Figure(
            data=self.traces,
            layout=dict(
                xaxis=self.get_xaxis(),
                yaxis=self.get_yaxis(),
                width=900,
                height=500,
                barmode="stack",  # plotly ignores barmode unless traces are bar
            ),
        )
        return fig


class StackedAreaChart(StackedChart):
    def __init__(self, data, xaxis_type, spec_role):
        super().__init__(data, xaxis_type, spec_role)
        self.traces = self._make_traces()

    def _make_traces(self):
        """Crates traces for each spec in data set."""
        spec_ids = self.specs.get_spec_ids_for_role(self.spec_role)
        traces = []
        for spec_id in spec_ids:
            key_level = list(self.data)
            spec_share = list(self.data.loc[self.data.index == spec_id, :].values[0])
            spec_color = "rgba(%d,%d,%d,0.7)" % self.specs.get_color(spec_id)
            trace = go.Scatter(
                x=key_level,
                y=spec_share,
                mode="lines",
                line=dict(width=1.5, color="black"),
                hoveron="points",
                hovertext="test",
                hovertemplate=self.hovertemplate["area+" + self.xaxis_type],
                fillcolor=spec_color,
                stackgroup="one",
                groupnorm="percent",
                name=self.specs.get_spec_name(spec_id).upper(),
            )
            traces.append(trace)
        return traces


class StackedBarChart(StackedChart):
    def __init__(self, data, xaxis_type, spec_role):
        super().__init__(data, xaxis_type, spec_role)
        self.traces = self._make_traces()

    def _make_traces(self):
        """Crates traces for each spec in data set."""
        spec_ids = self.specs.get_spec_ids_for_role(self.spec_role)
        traces = []
        for spec_id in spec_ids:
            key_level = list(self.data)
            spec_share = list(self.data.loc[self.data.index == spec_id, :].values[0])
            spec_color = "rgba(%d,%d,%d,0.7)" % self.specs.get_color(spec_id)
            traces.append(
                go.Bar(
                    name=self.specs.get_spec_name(spec_id).upper(),
                    x=key_level,
                    y=spec_share,
                    marker=dict(color=spec_color, line=dict(color="black", width=1)),
                    hoverlabel_align="right",
                    text=[self.specs.get_spec_name(spec_id).upper()] * len(key_level),
                    hoverlabel=dict(bgcolor="black"),
                    hovertemplate=self.hovertemplate["bar+" + self.xaxis_type],
                )
            )
        return traces
