# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State

import plotly.graph_objs as go

import pandas as pd
import io
import json

from operator import attrgetter




affiliations = set(df[df['sectionnamed']=='Affiliation']['sublist_name'])
instruments = set(df[df['sectionnamed']=='Instrument']['sublist_name'])

full_info = {'Overall': []}
full_info.update(lookup_sublists)

from plotly import colors
import numpy as np
from ast import literal_eval

def get_colors_from_name(colormapname, numbervalues, reverse=False):

    plotly_colors, plotly_scale = colors.convert_colors_to_same_type(colormapname)
    if reverse:
        plotly_colors.reverse()
    plotly_scale = np.array(plotly_scale)

    plotly_colors = np.array(list(map(literal_eval, [color[3:] for color in plotly_colors])))/255.0
    vmin = 0
    vmax = numbervalues
    values = np.arange(0, vmax)
    v = (values - vmin)/(vmax - vmin)
    closest_indices = [sorted(np.argsort(np.abs(plotly_scale - i))[0:2])  for i in v]
    newcolors = [colors.find_intermediate_color(plotly_colors[indices[0]], plotly_colors[indices[1]], value)
                  for indices, value in zip(closest_indices, v)]
    newcolors = [colors.label_rgb(colors.convert_to_RGB_255(i)) for i in newcolors]
    return newcolors

def generate_paper_table(dataframe):
    """
    Manually generate paper list with links to pigwidgeon for paper_id column
    """
    head = html.Thead(
        html.Tr(
            [html.Th(i) for i in dataframe.columns])
    )

    rows = []
    for i in range(len(dataframe)):
        row = []
        for col in dataframe.columns:
            value = str(dataframe.iloc[i][col])
            if col == 'paper_id':
                ref = 'http://kapili:5000/search/1/paper/{}'.format(value)
                row += [html.Td(html.A(href=ref, children=value))]
            else:
                row += [html.Td(value)]
        rows += [html.Tr(row)]
    body = html.Tbody(rows)
    return html.Table([head, body])



def generate_displaytab_layout(section):
    """
    Generate the tabs for each section
    """
    if section != 'Overall':
        content = dcc.Tab(label=section,
                           children=[
                               html.Div([
                                   html.Label('Subsections to include in display:'),
                                   html.Div(id='div-sublist-dropdown-{}'.format(section),
                                   children=[dcc.Dropdown(id='sublist-dropdown-{}'.format(section), multi=True,
                                                options=[{'label':i, 'value':i} for i in full_info[section]],
                                                value=[i for i in full_info[section]])]),

                                   html.Hr(),
                                   html.Div(id='display-selected-values-{}'.format(section)),

                               ])])
    else:
        content = dcc.Tab(label=section,
                           children=[html.Div([
                               html.Div(id='display-selected-values-{}'.format(section)),
                           ])
                                 ])
    return dcc.Tab(label=section, value=section, children=content)


# Callback to generate the section dropdown.
def generate_display_dropdown_callbacks(section):


    inputs = [Input('filtered-data', 'children')]
    output = Output('div-sublist-dropdown-{}'.format(section), 'children')
    @app.callback(output,inputs)
    def render_sublist_dropdown(jsoninfo):
        print('Rendering sublist dropdonw!')

        pdjson = None
        if jsoninfo is not None:
            pdjson = json.loads(jsoninfo).get(section, None)
        if pdjson:
            table = pd.read_json(pdjson, orient='split')
            columns = table.columns
            print('columns for display dropdown are', columns)
            dropdown = dcc.Dropdown(id='sublist-dropdown-{}'.format(section),
                                    multi=True,
                                    options=[{'label':i, 'value':i} for i in columns],
                                    value = [i for i in columns])
        else:
            dropdown= dcc.Dropdown(id='sublist-dropdown-{}'.format(section))
        return dropdown


def generate_render_display_functions(thesection):
    """
    This will return a (decorated) function
    that will generate the rendered display for
    a given section, including the entire tab.

    section: name of a section (str)
    """

    inputs = []

    inputs += [Input('filtered-data', 'children')]
    inputs += [Input('group-selecting', 'values')]
    inputs += [Input('color-dropdown', 'value')]
    if thesection != 'Overall':
        inputs += [Input('sublist-dropdown-{}'.format(thesection), 'value')]

    output = Output('display-selected-values-{}'.format(thesection), 'children')


    @app.callback(output, inputs)
    def render_display_func(*args):

        print('rendering {}'.format(thesection))
        section = thesection
        byyear = False
        reverse = False
        jsoninfo = args[0]
        checkboxes = args[1]
        colormap = args[2]
        if colormap == 'None':
            colormap = None
        if 'peryearwithin' in checkboxes:
            byyear = True
        if 'reverse' in checkboxes:
            reverse = True
        sublists = None
        if len(inputs) > 3:
            sublists = args[3]

        pdjson = None
        if jsoninfo is not None:
            pdjson = json.loads(jsoninfo).get(section, None)

        if pdjson:
            table = pd.read_json(pdjson, orient='split')
            # Only include requested sections:
            if sublists and sublists != []:
                # Ensure we keep the original order (might be more efficient to use the lookup table?)
                table = table[[i for i in table.columns if i in sublists]]
                #table = table[[i for i in table.columns]]# if i in sublists]]

            # Add up overall included years if requested.

            if not byyear and section != 'Overall':

                table = pd.DataFrame(table.sum(axis=0))
                table  = table.rename({0:'Publications'}, axis=1)

            tab_results = table.transpose().reset_index().fillna(0)


            tab = dash_table.DataTable(
                id='table',
                columns = [{"name": i, "id": i} for i in tab_results.columns],
                data=tab_results.to_dict('rows'),
                style_as_list_view=True,
                filtering=False,
                sorting=True,
            )

            bars = []
            if section == 'Overall':
                bars = [go.Bar(x=table.index, y=table['Publications'].values)]
            elif byyear is True:
                for key in table.index:
                    temp = table.loc[key]
                    bars.append(go.Bar(x=temp.index, y=temp.values, name=key))
            else:
                bars = [go.Bar(x=table.index, y=table['Publications'].values)]
            if colormap:
                colorway = get_colors_from_name(colormap, len(bars), reverse=reverse)
            else:
                colorway = None

            bar_layout = go.Layout(barmode='group',
                                   title='{}'.format(section),
                                   xaxis=dict(tickangle=45, automargin=True),
                                   yaxis=dict(title='Number of publications', automargin=True),
                                   colorway=colorway,
                               )
            graph = dcc.Graph(
                id = 'mainplot',
                figure={ 'data': bars, 'layout': bar_layout},
                config={'toImageButtonOptions': {'format':'png', 'filename':'{}-plot'.format(section)}},
                )
        else:
            graph = None
            tab = None
        print('calculated info for rendering {}'.format(thesection))
        return [graph, tab]

    return render_display_func





from dash_getinfo import get_pigwidgeon_info
df, sublists = get_pigwidgeon_info(['JCMT Science Paper', 'JCMT Theory Paper'], 1)
df['year'] = [i.year for i in df.pubdate]


# Create look up lists of sublists in correct DB order.
lookup_sublists = {}
sections = set([i.section for i in sublists])
for section in sections:
    temp = sorted([i.InfoSublist for i in sublists if i.section == section],
                  key=attrgetter('position_'))
    lookup_sublists[section] = [i.named for i in temp]


# Global values: do not change these within dash!


predefined_merge_sets = {
    'Observations': {'Large/Legacy Programs': ['JLS', 'LAP']},
    'Instrument': {'RxAs': ['RxA', 'RxA3', 'RxA3(M)'],
                   'Other': ['Other', 'AzTEC', 'RxB', 'RxW', 'Unknown'],
                   'Heterodyne': ['HARP', 'RxA3', 'RxA3(M)', 'RxW', 'RxA', 'RxB'],
                   'Continuum': ['SCUBA-2', 'SCUBA', 'UKT14'],
                   'Polarimetric': ['POL-2', 'SCUBA-POL'],
               },

    'Affiliation': {'International': ['Netherlands (JAC member)', 'International'],
                    'EAO members': ['China', 'Japan', 'Korea', 'Taiwan', 'Vietnam', 'Thailand'],
                    'Former JAC': ['Netherlands (JAC member)', 'UK', 'Canada'],
                    'core EAO': ['China', 'Japan', 'Korea', 'Taiwan'],}
}


jcmt_defaults = dict(
    default_papertypes = ['JCMT Science Paper', 'JCMT Theory Paper'],
    firstyear = 2013,
)



affiliations = set(df[df['sectionnamed']=='Affiliation']['sublist_name'])
instruments = set(df[df['sectionnamed']=='Instrument']['sublist_name'])

full_info = {'Overall': []}
full_info.update(lookup_sublists)





def get_results(datatable, section, years, byyear=True, order=None):
    """
    Given a dataset datatable, this will set it up to be displayed as a plot or table.

    Also reorder to order from 'order', assumign that is a list of columns

    The returned data set will  have a cateogrical axis.

    (For table, ideally transpose it so that years are along the top
    of the columns and long names are in the rows)
    """

    if years:
        newdatatable = datatable[datatable.year.between(years[0], years[1])]
    else:
        newdatatable = datatable
    if section != 'Overall':
        newdatatable = newdatatable[newdatatable['sectionnamed']==section]
        if len(newdatatable) > 0:
            if order:
                categories = pd.Categorical(values=order, categories=order, ordered=True)
                newdatatable['sublist_name'] = newdatatable['sublist_name'].astype(categories)

            if byyear:
                results = newdatatable.pivot_table(values=['paper_id'],
                                                   aggfunc=lambda x: len(set(x)),
                                                   columns=['sublist_name'],
                                                   index=['year'],
                                                   dropna=False)
                results.columns = results.columns.droplevel()
            else:
                results = newdatatable.pivot_table(values=['paper_id'],
                                                   aggfunc=lambda x: len(set(x)),
                                                   columns=['sublist_name'],
                                                   dropna=False)



                results = results.rename({'paper_id':'Publications'}, axis=1)


            results = results.rename_axis('', axis=1)
        else:
            results = pd.DataFrame()

    else:
        results = newdatatable.groupby(['year']).agg({'paper_id': lambda x: len(set(x))})
        results = results.rename({'paper_id':'Publications'}, axis=1)

    return results




minyear = min(df['year'])
maxyear = max(df['year'])

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions']=True


# Div to perform the basic seelction
basic_selection =  html.Div([html.H2('Data Selection Options'),
                             html.Label('Years to include:'),
                             dcc.RangeSlider(id='year-select', count=1, min=minyear, max=maxyear,
                                             step=1, value=[minyear, maxyear],
                                             marks={i: '{}'.format(i) for i in range(minyear, maxyear+1)},),
                             html.Br(),
                             html.Label('Search within ADS affiliation string:'),
                             dcc.Input(id='aff-text-string', placeholder='Text found within affiliations', type='text', value=''),
                             dcc.Checklist(id='affiliation-search-type',
                                           options=[{'label': "Only search within the first author's affiliation",
                                                     'value': "affsearch-firstonly"}],
                                           values=['affsearch-firstonly'],),
                         ])

# Advanced selection tab contents
# SElection dropdown: 80%,
# display: inline-block
# select-all button: vertical-align top
def generate_infosection_selection_layout(section, sublist):

    # Get the default merge sections
    if section in predefined_merge_sets:
        mergers = predefined_merge_sets[section]
        jsoninfo = json.dumps(mergers)
        options = [{'label': '{}: {}'.format(key, values), 'value': key} for key, values in mergers.items()]
        checklist = dcc.Checklist(id='merger-tickboxes-{}'.format(section),
                                  options=options, values=[])
    else:
        jsoninfo = None
        checklist = dcc.Checklist(id='merger-tickboxes-{}'.format(section),options=[], values=[])

    children=html.Div([
        html.Label('Select by marked {}:'.format(section)),
        html.Div(className='selection-dropdown', children=[
            dcc.Dropdown(id='{}-dropdown'.format(section), multi=True,
                         options=[{'label':i, 'value':i} for i in sublist],
                         value=[i for i in sublist],),
        ]),
        html.Button('Select All', id='btn-{}'.format(section), className='select-all'),

        html.Label('Merge specific categories:'),

        html.Div(className='selection-dropdown', children=[
            dcc.Dropdown(id='{}-merge-dropdown'.format(section), multi=True,
                         options=[{'label':i, 'value':i} for i in sublist],
                         value=[]),
        ]),
        dcc.Input(id='{}-merge-input'.format(section),
                  placeholder='new name',
                  type='text',
                  value='', className='select-all'),
        html.Button('Create merger', id='btn-merge-{}'.format(section)),
        html.Div(id='merged-values-{}'.format(section), children=[
            html.Div(id='merger-message-{}'.format(section), children=None),
            html.Div(id='merged-values-{}-hidden'.format(section), hidden=True, children=jsoninfo),
            html.Div(id='merged-values-{}-display'.format(section), hidden=True,
                     children=[checklist]),
        ])
    ])

    content = dcc.Tab(label=section,
                      value=section,
                      children=children)
    return content







# Advanced selection Div.
as_sections = lookup_sublists.keys()
advanced_selection = html.Div([
    """If all options for a given section are left selected, no filtering is performed.""",
    dcc.Tabs(id="advanced-selection-tabs", value='Affiliation',
             children=[generate_infosection_selection_layout(section, lookup_sublists[section])
                       for section in as_sections]
             ),
    html.Br(),
    html.Button('Filter Data', id='btn-filter'),
    html.Div(id='advanced-selection-tabs-content'),
])
# Get a list of the as_section states that are needed for callbacks
as_section_states = [State('{}-dropdown'.format(i), 'value') for i in as_sections]

# generator to create the functions for the buttons
def generate_as_selectall_button_functions(section):

    @app.callback(Output('{}-dropdown'.format(section), 'value'),
                  [Input('btn-{}'.format(section), 'n_clicks')])
    def update_output(n_clicks):
        return [i for i in lookup_sublists[section]]
    return update_output

for section in as_sections:
    generate_as_selectall_button_functions(section)

# Now the merge callbacks
# 1: callback to write merges into a the hidden div merged-values-{section}
def generate_merge_functions(section):
    @app.callback(Output('merged-values-{}'.format(section), 'children'),
                  [Input('btn-merge-{}'.format(section), 'n_clicks')],
                  [State('merged-values-{}'.format(section), 'children'),
                   State('{}-merge-dropdown'.format(section), 'value'),
                   State('{}-merge-input'.format(section), 'value'),
                   State('merger-tickboxes-{}'.format(section), 'values'),]
              )
    def merge_function(n_clicks, existingchildren, names_to_merge, newname, selected_mergers):
        message = None
        print('in merge function', 'names_to_merger are:', names_to_merge, newname)


        if n_clicks and (newname is None or newname == ''):
            message = 'You must provide a new name for your merged set'
        if n_clicks and (names_to_merge  is None or names_to_merge == []):
            message = 'You must provide values to merge'



        jsoninfo = existingchildren[1]['props']['children']
        print('jsoninfo is: ', jsoninfo, type(jsoninfo))
        if jsoninfo  and jsoninfo != [] and jsoninfo != [None]:
            mergers = json.loads(jsoninfo)

        else:
            mergers = {}

        # Check names_to_merge don't exist in existing values:
        if newname in mergers.keys():
            message = 'Your new name is already the name of a merge set'
        for i in names_to_merge:
            if i in [j for i in mergers.values() for j in i] and i in selected_mergers:
                message = 'A value you gave is already in a (selected) merge set!'
        if not n_clicks:
            message = ' '
        if not message:
            mergers[newname] = names_to_merge
            jsoninfo = json.dumps(mergers)

        # merged output needs to be a list of tick boxes:
        #dcc.Checklist(id='merger-tickboxes-{}'.format(section),
        #              options
        options = []

        options = [{'label': '{}: {}'.format(key, values), 'value': key} for key, values in mergers.items()]
        values = [key for key in mergers if key in selected_mergers]
        checklist = dcc.Checklist(id='merger-tickboxes-{}'.format(section),
                                  options = options,
                                  values = values)
        checklisttext = 'Existing mergers: (select to apply these when filtering data)'
        #formatted_output = ['{}: {}'.format(key, values) for key, values in mergers.items()]

        #interleave formatted data with new lines:
        #formatted_output = [elem for x in formatted_output for elem in (x, html.Br())][:-1]
        #print(formatted_output)
        children = [html.Div(id='merger-message-{}'.format(section), children=[message]), html.Div(id='merged-values-{}-hidden'.format(section), hidden=True, children=jsoninfo),
                    html.Div(id='merged-values-{}-display'.format(section), children=[checklisttext, checklist]),
                    ]
        return children

for section in as_sections:
    generate_merge_functions(section)


#2: include the values in the filtering.
merger_section_states = [State('merged-values-{}-hidden'.format(i), 'children') for i in as_sections]
merger_checklist_states = [State('merger-tickboxes-{}'.format(i), 'values') for i in as_sections]

selection_results = html.Div([
    html.H2('Summary of selected data'),
    html.Div(id='filtered-data-parent', children=[
        html.Div(id='filtered-data', style={'display': 'none'}),
        html.Div(id='filtered-data-warnings'),
        html.Div(id='filtered-data-summary', children=[html.H4(id='summary_title'),
                                                       html.Div(id='filtered_table_div',
                                                                style={'display': 'none'})]),
    ]),
])


# Callbacks for the display tabs
for section in full_info.keys():
    generate_display_dropdown_callbacks(section)
    generate_render_display_functions(section)



displaytabs_children = [generate_displaytab_layout(i) for i in full_info.keys()]


app.layout = html.Div(
    style={'max-width': '50em', 'margin': 'auto', 'margin-top': '5em'},

    children=[
        basic_selection,
        html.Br(),
        advanced_selection,
        selection_results,
        #html.Div(id='filtered-data-parent', children=[
        #    html.Div(id='filtered-data', style={'display': 'none'}),
        #    html.Div(id='filtered-data-warnings')
        #]),
        html.Hr(),

        html.Div([html.H2('Display Results'),
                  html.Label('Select colorscale for plots'),
                  dcc.Dropdown(id='color-dropdown', multi=False,
                               options=[{'label':i, 'value':i} for i in list(colors.PLOTLY_SCALES.keys())
                                        + ['None']],
                               value='Viridis'),
                  dcc.Checklist(id='group-selecting',
                                options=[{'label': 'Reverse color scale', 'value': 'reverse'},
                                         {'label': 'Show results by year within each subsection',
                                          'value': 'peryearwithin'}],
                                values=['peryearwithin']),

                  dcc.Tabs(id="display-tabs", value='Overall',
                           children=displaytabs_children),
              ]),

    ])



def filter_data_mergecats(df, mergerdict):
    datatable = df.copy(deep=True)
    for section in mergerdict:
        for newname in mergerdict[section]:
            valuestoupdate = mergerdict[section][newname]
            mask = (datatable['sectionnamed']==section) & \
                   (datatable['sublist_name'].isin(valuestoupdate))
            datatable.loc[mask, 'sublist_name'] = newname

    print(mergerdict)

    return datatable



# Callbacks for data selection!
def filter_data_sublistname(datatable, years, sectiondict):
    print(years)
    filtered = datatable[datatable.year.between(years[0], years[1])]

    paper_ids = None
    for name, vals in sectiondict.items():
        print(name, vals)
        if vals  and set(vals) != set(lookup_sublists[name]) and len(vals) > 0:
            mask = (filtered['sectionnamed']==name)&(filtered['sublist_name'].isin(vals))
            pids = set(filtered['paper_id'][mask])
            if paper_ids is None:
                paper_ids = pids
            else:
                paper_ids = paper_ids & pids
    if paper_ids:
        filtered = filtered[filtered['paper_id'].isin(paper_ids)]
    return filtered




# filter the data, store it in the output and summarise it for viewing.
@app.callback(Output('filtered-data-parent', 'children'),
              [Input('btn-filter', 'n_clicks')],
              [State('year-select', 'value'),
               State('aff-text-string', 'value'),
               State('affiliation-search-type', 'values')] + as_section_states + merger_section_states + merger_checklist_states
        )
def filter_data_store_and_summarize(n_clicks, years, afftext, affsearchtype, *args):
    print(affsearchtype, type(affsearchtype))
    print('filter_data_store_and_summarize')
    sections = list(as_sections)
    section_dict = dict(zip(as_sections, args[0:len(as_sections)]))

    merger_dict = {}
    mergerargs = args[len(as_sections):2*len(as_sections)]
    mergerchecklistargs = args[2*len(as_sections):3*len(as_sections)]


    summarys = {}


    messages = []
    for i, sect  in enumerate(as_sections):
        mergers = mergerargs[i]
        selected_mergers = mergerchecklistargs[i]
        if mergers and len(selected_mergers) > 1:
            mergers = json.loads(mergerargs[i])


            # Check that you don't have names in multiple mergers.
            valone = [mergers.get(i, None) for i in selected_mergers]

            values = [j for i in selected_mergers for j in mergers[i]]
            if len(values) != len(set(values)):
                print('Warning: name for section %s contained in multiple selected mergere' % sect)
                messages += ['Warning: a name was contained in multiple selected mergers in section {}. Not merging'.format(sect)]

            elif len(selected_mergers) > 0:
                newmergers = {}
                for newname in selected_mergers:
                    mergedvalues = mergers[newname]
                    vallist = section_dict[sect]
                    location = vallist.index(mergedvalues[0])
                    vallist[location] = newname
                    if len(mergedvalues) > 1:
                        [vallist.remove(j) for j in mergedvalues[1:]]
                    section_dict[sect] = vallist
                    newmergers[newname] = mergedvalues


                merger_dict[sect] = newmergers


    # Update the data, and also update the section_dict
    filtered = filter_data_mergecats(df, merger_dict)

    filtered = filter_data_sublistname(filtered, years, section_dict)
    filtered = filter_data_afftext(filtered, afftext, affsearchtype)

    # Create a summary table of papers.
    papers = set(filtered['paper_id'])
    mask = (df['paper_id'].isin(papers))&(df['position']==0)
    filtered_table = df[mask][['paper_id', 'title', 'pubdate', 'author']].drop_duplicates()
    filtered_table = generate_paper_table(filtered_table)

    # Summarize what was done: years selected, affiliation checking, mergers carried out:
    summary = ['{} Papers are present in this selection'.format(len(papers))] + ['']
    summary += ["Papers from {} to {} are being examined.".format(years[0], years[1])]
    if afftext and afftext != '':
        text = 'Only papers where the string "{afftext}" is contained {afftype} are being examined'
        if affsearchtype == ['affsearch-firstonly']:
            text = text.format(afftext=afftext, afftype="within the first author's affiliation")
        else:
            text = text.format(afftext=afftext, afftype="in any author's affiliation")
        summary += [text, '']
    if merger_dict:
        text = ['New categories have been formed by merging/renaming old categories.', '']
        for section, mergers in merger_dict.items():

            text += ['In section {}:'.format(section)]
            text += ['{} formed from {}'.format(mergername, str(mergeritems))
                     for mergername, mergeritems in mergers.items()]
            text += ['']
        summary += text

    # Inser a line break inbetween each item
    summary = [x for line in summary for x in (line, html.Br())]
    print(summary)




    # Now get the results info for all the graphs:
    resultsdict = {}
    for section in full_info.keys():
        results = get_results(filtered, section, years, byyear=True, order=section_dict.get(section, None))
        resultsdict[section] = results.to_json(date_format='iso', orient='split')


    return [html.Div(id='filtered-data', style={'display': 'none'}, children=json.dumps(resultsdict)),
            html.Div(id='filtered-data-warnings', children=messages),
            html.Div(id='filtered-data-summary',
                     children=[html.Div(summary),
                               html.H4("Table of papers (click here to hide/show)", id='summary_title'),
                               html.Div(children=filtered_table, style={'display': 'none'},
                                        id='filtered_table_div')
                           ]
                     ),
    ]

@app.callback(Output('filtered_table_div', 'style'),
              [Input('summary_title', 'n_clicks')])
def show_hide_summarytable(n_clicks):
    if n_clicks %2 == 0:
        return {'display': 'none'}
    else:
        return {}




def filter_data_afftext(datatable, afftext, searchtype):
    if afftext is not None and afftext != '':
        if searchtype == ['affsearch-firstonly']:
            datatable = datatable[datatable['position']==0]
        paper_ids = datatable['paper_id'][datatable['affiliation'].str.contains(afftext)]
        return datatable[datatable['paper_id'].isin(paper_ids)]
    else:
        return datatable




if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
