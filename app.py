import pandas as pd
import plotly.express as px
import json

data = pd.read_csv("netflix_titles.csv")
map_json = json.load(open("countries.json", "r"))

countries = []

for feature in map_json["features"]:
      countries.append(feature["properties"]["geounit"])

countries=[*set(countries)]
countries.sort()

country_df = pd.DataFrame(countries, columns =['Country'])
year_df = pd.DataFrame(list(range(1942, 2022)), columns =['Year'])

countries_df = country_df.merge(year_df, how='cross')

data['country_individual'] = data['country'].str.split(',')
data_exploded = data.explode(['country_individual'])
data_exploded['country_individual'] = data_exploded['country_individual'].str.strip()

movies_yearly = data_exploded.groupby(['country_individual', 'release_year'])['type'].apply(lambda x: (x=='Movie').sum()).reset_index(name='Movies')
shows_yearly = data_exploded.groupby(['country_individual', 'release_year'])['type'].apply(lambda x: (x=='TV Show').sum()).reset_index(name='Shows')

stats_yearly = pd.merge(movies_yearly, shows_yearly, on = ['country_individual', 'release_year'])
stats_yearly['All'] = stats_yearly['Movies'] + stats_yearly['Shows']

stats_yearly =  pd.merge(countries_df, stats_yearly, how='left', left_on = ['Country', 'Year'], right_on = ['country_individual', 'release_year'],)
stats_yearly.drop(['country_individual', 'release_year'],axis=1, inplace=True) #inplace - return copy or perform in place
stats_yearly = stats_yearly.fillna(0);
stats_yearly = stats_yearly.sort_values(by =  'Year')

stats_yearly = stats_yearly.reset_index(drop=True)


stats_total = stats_yearly.groupby(['Country']).sum()
stats_total.drop(['Year'],axis=1, inplace=True) 
stats_total = stats_total.reset_index()

# # DASH

from dash import Dash, html, dcc, Input, Output, dash_table

app = Dash(__name__)
server = app.server

#*******APP LAYOUT**************

app.layout = html.Div( #this is the main structure of the application
    style={'backgroundColor':'#323130', #css styling
        'height': '100%',
        'color': 'white',
        'margin': 0,
        'padding': '15px' 
    }, 
    
    children=[ #all elements in the main application layoud should be specified here
        #****************************HEADER*************************************
        html.H1(children='Netflix in Data'), #stylized text using H1 html tag

        dcc.Markdown('### Visualisation of Netflix Movie and TV Show origins'),#stylized text using markdown styling  
    
        html.Hr(),#horizontal line
    
        #****************************Controls*************************************
        html.Div(children=[ #html div element with 2 child nodes - text and radiobutton container (with radio buttons as children)
            'Content type:', 
            dcc.RadioItems(['Movies', 'Shows', 'All'], #options
                           'All', #default option
                           id='content', #ID - this is used in callbacks to identify input and output elements
                           inline=True)], #inline layout of radiobuttons
            style={'width': '100%', 'display': 'inline-flex'} #css styling
        ),
    
        html.Div(children=[ #html div element with 2 child nodes - text and radiobutton container (with radio buttons as children)
            'Fixed color range:', 
            dcc.RadioItems(['Fix', 'Auto'], #options
                       'Auto', #default option
                       id='fix_scale', #ID - this is used in callbacks to identify input and output elements
                       inline=True)], #inline layout of radiobuttons
            style={'width': '100%', 'display': 'inline-flex'} #css styling
        ),
    
        #****************************Map*************************************   
        
        html.Div( #html div element with one child node - a graph container
            dcc.Graph(id='map'), #id is used in callbacks to identify input and output elements
            style={'width': '50%', 'display': 'inline-block'}
        ),
    
        #****************************Timeline*************************************   
        
        html.Div(#html div element with one child node - a graph container
            dcc.Graph(id='timeline'), #id is used in callbacks to identify input and output elements
            style={'width': '50%', 'display': 'inline-block'}),
    
    
        #****************************Slider*************************************   
        dcc.Markdown('**Years**'), #stylized text using markdown styling 
        html.Div([#html div element with one child node - a year slider
            dcc.Slider(1942, 2021, step = 1, value=2021, id='slider',
                    marks={i: '{}'.format(i) for i in range(1942,2021,10)},
                    tooltip={'placement': 'bottom', 'always_visible': True})
            ], 
            style={'width': '50%', 'display': 'inline-block'}),


         #****************************Table*************************************
         html.Div(#html div element with no children (so far)
            children=[],
            id="table_container" #ID - this is used in callbacks to identify input and output elements (we will place the table in here)
        ),
        
        #****************************Debug Output*************************************
        html.Div([
            dcc.Markdown(' **Debug output** '), html.Pre(id='click-data')]),#element for pre-formatted text output, we will use callback to place 'clickData' (data generated on click) here
    ],
 )


#**************FUNCTIONS*****************************

def get_map(content, year, fix): #function generating Plotly choropleth map; takes content type, year, and a type of scale as input
      stats_map = stats_yearly[stats_yearly["Year"] == year] #selection of data for given year
      if not stats_map.empty:
          range_max = 450 if fix=='Fix' else max(1, max(stats_map[content]))
          fig=px.choropleth(stats_map, #data
                      geojson=map_json,
                      featureidkey='properties.geounit', #property in geojson - the values must match the values of 'locations'
                      locations='Country',#column in dataframe - the values must match the values of 'featureidkey'
                      color= content,  #dataframe
                      hover_data=['Movies','Shows'],
                      range_color=(0, range_max), 
                      color_continuous_scale='Reds',
                      projection='equirectangular', 
                      title='map'
                      )
        
          fig.update_geos(visible=False)
          fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
          fig.update_layout(geo_bgcolor="#323130", plot_bgcolor= "#323130", paper_bgcolor= "#323130", font_color="white",)
          return fig


def get_country_graph(country): #function generating Plotly barchart, takes country as input
      timeline = stats_yearly[stats_yearly['Country'] == country] #selecting country data
      bars = px.bar(timeline, #data
                    x="Year",
                    y=["Movies", "Shows"],
                    title="Timeline: " + country,
                    barmode = 'group', #group or stack
                    color_discrete_sequence=["white", "red"],)
      bars.update_layout(plot_bgcolor= "#323130", paper_bgcolor= "#323130", font_color="white")
      return bars

def get_table(country, year, content): #function generating dash table
    table_df = data_exploded[(data_exploded.release_year == year) & (data_exploded.country_individual == country) & (data_exploded.country_individual == country)] [['type','title','director','rating','listed_in']]
    table_df = table_df[(table_df.type == 'TV Show')] if content == 'Shows' else table_df
    table_df = table_df[(table_df.type == 'Movie')] if content == 'Movies' else table_df
    return dash_table.DataTable(
                    table_df.to_dict('records'),
                    id="table",
                    columns=[{"name": i, "id": i} for i in table_df.columns],
                    style_header={
                        'backgroundColor': 'black',
                        'fontWeight': 'bold'
                    },
                    style_cell={'backgroundColor': '#999999'},
                )

#*************CALLBACKS*****************************************
#each callback is triggered by changes of element properties defined as Input in the header, and places the return value into the element property specified as Output 
#the 'Input's' of the cllaback header define the input properties of the callback function, the order in the Inputs in the header dictates the order of the function parameters

#radio/slider/fix->map
@app.callback( 
    Output('map', 'figure'), #return value will be inserted into 'figure' property of element with id 'map' (a graph container, see above)
    Input('content', 'value'), #callbeck is triggered by change of 'value' property of element with id 'content' (radio buttons)
    Input('slider', 'value'), #callbeck is triggered by change of 'value' property of element with id 'slider' (timeline slider)
    Input('fix_scale', 'value') #callbeck is triggered by change of 'value' property of element with id 'fix_scale' (radio buttons)
)
def update_map(content, year, fix): #the input parameters are: 'value' property of element with id 'content'; 'value' property of element with id 'slider'; 'value' property of element with id 'fix_scale' 
    fig = get_map(content, year, fix) #create map
    return fig  

#map->barchart
@app.callback(
    Output('timeline', 'figure'), #return value will be inserted into 'figure' property of element with id 'timeline' (a graph container, see above)
    Input('map', 'clickData')  #callbeck is triggered by change of 'clickData' property of element with id 'map' (a graph container where we put the map)
)
def update_timeline(clickData): #the input parameters are: 'clickData' property of element with id 'map' 
    country = "Czech Republic" #setting default country in case clickData is None
    if clickData is not None:
        country= clickData['points'][0]["location"] #extracting 'location' out of clickData - see the structure of ClickData in the debug output of the app
    bars = get_country_graph(country) #create timeline
    return bars
    

#map, content radiobuttons, year slider-> table
@app.callback(
    Output("table_container", "children"),
    Input('content', 'value'),
    Input('slider', 'value'),
    Input('map', 'clickData')
)
def display_table(content, year, clickData):
    if clickData is not None:
        country= clickData['points'][0]["location"]
        return get_table(country, year, content)

#map -> debug output - displaying clickData for debug purposes
@app.callback(
    Output('click-data', 'children'),
    Input('map', 'clickData')
)
def update_data(clickData):
    if clickData is not None:
        country= clickData['points'][0]["location"]
        return json.dumps(clickData, indent=2)

#timeline barchart -> slider
@app.callback(
    Output("slider", "value"),
    Input('timeline', 'clickData'),
)
def update_year(clickData):
    year = 2021
    if clickData is not None:
            year = clickData['points'][0]["x"]
    return year

#********RUNNING THE APP*************************************************
if __name__ == '__main__':
    app.run_server(jupyter_mode="external", debug=False) 






