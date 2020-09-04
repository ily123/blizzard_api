"""
This module draws the figure showing spec distribution
vs key level
"""


import pandas as pd
import plotly.graph_objects as go
import blizzcolors
import importlib
importlib.reload(blizzcolors)


class RidgePlot:
    """Draws the ridge plot."""
   
    def __init__(self, data):
        """Inits with the formatted pandas dataframe.
   
        Params
        ------
        data : DataFrame
            spec should be the row, and level of key the columns
        """
        self.data = data # the table should already be pivoted
        self.summary = self.get_summary_table(data)
    
    @staticmethod
    def find_highest_key(row):
        """Finds index of the last non-zero int in list."""
        highest_key_index = None
        for i, a in enumerate(row):
            if a != 0:
                highest_key_index = i
        highest_key_level = highest_key_index + 2 #key level starts with 2
        return highest_key_level 
 
    def get_summary_table(self, data):
        """Computes total population and best key for each spec."""
        summary = pd.DataFrame(data.index)
        summary['total_run'] = data.sum(axis=1).values
        summary['best_key'] = data.apply(
            lambda x: self.find_highest_key(x) , axis=1).values
        return summary
 
    def sort_summary(self, sort_by = 'best_key'):
        if sort_by not in ['best_key', 'total_run']:
            raise ValueError(('Data can be sorted either by best_key'
                'or by total_run number of runs'))
        sort_order = ['best_key', 'total_run'] 
        if sort_by == 'total_run':
            sort_order = sort_order[::-1]
        sorted_summary = self.summary.sort_values(
            by = sort_order, ascending = False)
        return sorted_summary
   
    # generate_components()
    # self.annotations = self.get_annotations()
    # self.layout = self.get_layout()
    # 
    # assemble_figure():
    # fig = go.Figure()
    # fig.data = self.traces
    # fig.layout = self.layout
    # fig.update_layout(annotations=annotations)
    # return fig
    
    def generate_components(self):
        """Generates plotly figure components."""
        sorted_summary = self.sort_summary(sort_by = 'best_key')
        self.traces = self.construct_traces(sorted_summary)
        self.annotations = self.construct_annotations(sorted_summary)
        self.buttons = self.construct_buttons()
    
    def assemble_components(self):

        fig = go.Figure(data = self.get_all_traces())
        fig.update_layout(width=900, height=1500, showlegend=False)
        fig.update_layout(updatemenus = self.buttons)
        fig.update_layout(annotations = self.get_all_annotations())
        return fig

 
    def construct_traces(self, sorted_summary):
        """Makes line/fill traces of the data distribution."""    
        key_levels = list(self.data)
        key_levels_x = [i - 2 for i in list(key_levels)] # x =0, key - 2
        vertical_offset = 300_000
        num_specs = len(self.summary)
        specs = blizzcolors.Specs()
        traces = {}
        for index, row in enumerate(list(sorted_summary.values)):
            spec_id, total_runs, best_key_level  = row
            spec_color = 'rgba(%d,%d,%d,0.9)' % specs.get_color(spec_id)
            runs = self.data.loc[self.data.index == spec_id].values[0] 
            #horizontal baseline to underline each distribution
            baseline_y = vertical_offset * (num_specs - index)
            baseline = self.get_ridge_baseline(x = key_levels_x,
                y = [baseline_y for i in range(num_specs)])
            #the distribution of runs vs key level (the star of the show)
            ridge = self.get_ridge(
                x = key_levels_x,
                y = [baseline_y + run for run in runs],
                hover_y = runs,
                color = spec_color, 
                name = specs.get_spec_name(spec_id))
            traces[spec_id] = {'ridge': ridge, 'baseline': baseline}
        return traces
    
    def get_ridge_baseline(self, x, y):
        """Creates baseline for distibution (ridge)."""
        trace = go.Scatter(
            x = x, y = y,
            line = dict(width = 0.5, color = 'black'),
            hoverinfo = 'skip'
        )
        return trace
  
    def get_ridge(self, x, y, hover_y, color, name):
        """Creates distribution plot (ridge)."""
        trace = go.Scatter(name = name.upper(),
            x = x, y = y,
            fill = 'tozerox', 
            fillcolor = color,
            line = dict(width = 1, color = 'black', shape = 'spline'),
            text = [f'{y:,}' for y in hover_y], 
            customdata = [i + 2 for i in x],
            hovertemplate = 'KEY LEVEL: +%{customdata}<br>RUNS: %{text}' 
        )      
        return trace
    
    def get_all_traces(self):
        """Extracts raw trace objects from trace dict."""
        trace_list = []
        for traces in self.traces.values():
            trace_list.append(traces['ridge'])
            trace_list.append(traces['baseline'])
        return trace_list

    def construct_annotations(self, sorted_summary):
        """Make best key annotations."""
        annotations = {}
        vertical_offset = 300_000
        num_specs = len(sorted_summary)
        for index, row in enumerate(list(sorted_summary.values)):
            spec_id, _, best_key_level  = row
            baseline_y = vertical_offset * (num_specs - index)
            anno = self.get_best_key_annotation(
                x = best_key_level - 2,
                y = baseline_y, text = '+%d ' % best_key_level) 
            annotations[spec_id] = anno 
        return annotations

    def get_recolor_pattern(self, keep_role):
        """Generates color list that informs recolor of the traces.
        
        Given a spec role, recolors all traces not of that role to gray.

        Parameters
        ----------
        keep_role : str
            spec role ('tank', 'healer', 'mdps', 'rdps')

        Returns
        -------
        recolor : list
            list of colors, where color at index i corresponds to trace at 
            index i in fig.data
        """
        valid_roles = ['tank', 'healer', 'mdps', 'rdps']
        keep_role = keep_role.lower()
        if keep_role not in valid_roles:
            raise ValueError('Spec role invalid. Must be one of: %s')
        recolor = []
        specs = blizzcolors.Specs()
        custom_gray = 'rgba(0,0,0,0.3)' 
        for spec_id, spec_traces in self.traces.items():
            spec_role = specs.get_role(spec_id)
            #reassign color based on spec role
            new_ridge_color = None
            if spec_role == keep_role:
                new_ridge_color = spec_traces['ridge'].fillcolor
            else:
                new_ridge_color = custom_gray 
            #keep baseline the original color
            baseline_color = spec_traces['baseline'].line.color
            recolor.append(new_ridge_color)
            recolor.append(baseline_color)
        return recolor
   
    def keep_annotations(self, keep_role):
        """Makes annotation list based on spec role."""
        valid_roles = ['tank', 'healer', 'mdps', 'rdps']
        keep_role = keep_role.lower()
        if keep_role not in valid_roles:
            raise ValueError('Spec role invalid. Must be one of: %s')
        keep_annotations = []
        specs = blizzcolors.Specs()
        for spec_id, annotation in self.annotations.items():
            spec_role = specs.get_role(spec_id)
            if spec_role == keep_role:
                keep_annotations.append(annotation)
        return keep_annotations 
             
    def construct_buttons(self):
        """Creates interactive buttons for the figure."""    
        role_selector = self.make_role_selector_buttons() 
        anno_display = self.make_annotation_button()
        return [role_selector, anno_display]

    def make_annotation_button(self):
        """Creates hide/show annotation button."""
        default_annotations = self.get_all_annotations()
        anno_display = dict(
            type = 'buttons', direction = 'down',
            buttons = [
                dict(args = [{'annotations': []}],
                    label = 'CLEAR', method = 'relayout')
            ],
            showactive = False
        )
        return anno_display

    def make_role_selector_buttons_old(self):
        """Creates row of bottons that recolor plot based on spec role."""
        default_colors = self.get_default_colors()
        role_selector = dict(
            type = 'buttons', direction = 'down',
            buttons = [
                dict(args=[{'fillcolor': default_colors},
                    {'annotations': self.get_all_annotations()}],
                    label = 'ALL', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('tank')}],
                    label = 'TANK', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('healer')}],
                    label = 'HEALER', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('mdps')}],
                    label = 'MELEE', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('rdps')}],
                    label = 'RANGE', method = 'update')
            ]
        )
        return role_selector
    
    def make_role_selector_buttons(self):
        """Creates row of bottons that recolor plot based on spec role."""
        default_colors = self.get_default_colors()
        role_selector = dict(
            type = 'buttons', direction = 'down',
            buttons = [
                dict(args=[{'fillcolor': default_colors},
                    {'annotations': self.get_all_annotations()}],
                    label = 'ALL', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('tank')},
                    {'annotations': self.keep_annotations('tank')}],
                    label = 'TANK', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('healer')},
                    {'annotations': self.keep_annotations('healer')}],
                    label = 'HEALER', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('mdps')},
                    {'annotations': self.keep_annotations('mdps')}],
                    label = 'MELEE', method = 'update'),
                dict(args=[{'fillcolor': self.get_recolor_pattern('rdps')},
                    {'annotations': self.keep_annotations('rdps')}],
                    label = 'RANGE', method = 'update')
            ]
        )
        return role_selector

    def get_default_colors(self):
        """Extracts colors from traces."""
        default_colors = []
        for spec_traces in self.traces.values():
            default_colors.append(spec_traces['ridge'].fillcolor)
            default_colors.append(spec_traces['baseline'].line.color)
        return default_colors
    
    def get_all_annotations(self):
        """Returns all annotations that figure shows by default."""
        x = [a for a in self.annotations.values()]
        return x
 
    def get_best_key_annotation(self, x, y, text):
        """Creates text annotation of each spec's best key."""
        annotation = dict(x = x, y = y, text = text,
            font = dict(color = 'black', size = 15,
                        family = 'Monaco, regular'),
            align = 'center',
            showarrow = True, ax = 0, ay = -15,
            arrowsize = 2, arrowwidth = 1, arrowhead = 6,
            #arrowcolor = 'rgba(0,0,0,0.75)'
            arrowcolor = 'gray'
        )
        return annotation 
