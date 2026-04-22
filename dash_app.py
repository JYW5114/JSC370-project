from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv("fire.csv", low_memory=False)
time_cols = ['TFS_Alarm_Time', 'TFS_Arrival_Time', 'Fire_Under_Control_Time', 'Hourly_Timestamp']
for col in time_cols:
    df[col] = pd.to_datetime(df[col])
df['Control_Duration'] = (df['Fire_Under_Control_Time'] - df['TFS_Arrival_Time']).dt.total_seconds()
df['Hour_of_Day'] = df['Hourly_Timestamp'].dt.hour
df['is_weekend'] = df['Hourly_Timestamp'].dt.dayofweek >= 5

def categorize_event(x):
    x = str(x)
    if "Fire" in x or x.startswith("FI"):
        return "Fire"
    else:
        return "Other"
df["Event_Category"] = df["Initial_CAD_Event_Type"].apply(categorize_event)
df = df[df["Event_Category"]=="Fire"]

df_train_val, df_test = train_test_split(df, test_size=0.2, random_state=42)
df_train, df_val = train_test_split(df_train_val, test_size=0.2, random_state=42)

df_analysis = df_train[(df_train['Control_Duration'] > 0) & (df_train['Control_Duration'] < 14400)].copy()
df_analysis['Incident_Station_Area'] = df_analysis['Incident_Station_Area'].astype(int)

df_analysis['Scale'] = df_analysis['Number_of_responding_apparatus'].apply(lambda x: 'Small' if x <= 10 else 'Large')
def categorize_property(x):
    if pd.isna(x):
        return "Other"
    
    code = x.split(" - ")[0].strip()
    
    residential = {"301", "302", "303", "321", "322", "323", "311", "331"}
    commercial = {"151", "501", "405", "334"}
    vehicles = {"901", "902", "903", "837"}
    garages = {"365", "603"}
    infra = {"896", "144", "846", "891"}
    waste = {"848"}
    
    if code in residential:
        return "Residential"
    elif code in commercial:
        return "Commercial"
    elif code in vehicles:
        return "Vehicles"
    elif code in infra:
        return "Infrastructure"
    elif code in waste:
        return "Waste"
    elif code in garages:
        return "Garages"
    else:
        return "Other"
    
df_analysis["Property_Group"] = df_analysis["Property_Use"].apply(categorize_property)
df_analysis["Loss_Level"] = pd.qcut( df_analysis["Estimated_Dollar_Loss"], q=3, labels=["Low", "Medium", "High"] )

df_analysis["Sprinkler_System_Presence"] = df_analysis["Sprinkler_System_Presence"].fillna("9 - Undetermined")
loss_map = {"Low": 0, "Medium": 1, "High": 2}

main_groups = ["Residential", "Commercial"]

df_analysis["Property_Group_Plot"] = df_analysis["Property_Group"].where(
    df_analysis["Property_Group"].isin(main_groups),
    "Other"
)

df_analysis["Scale"] = pd.Categorical(
    df_analysis["Scale"],
    categories=["Small", "Medium", "Large"],
    ordered=True
)

df = df_analysis.copy()
df = df[df["Sprinkler_System_Presence"] != "9 - Undetermined"]

loss_map = {"Low": 0, "Medium": 1, "High": 2}

sprinklers = {
    "All": None,
    "Full": "1 - Full sprinkler system present",
    "Partial": "2 - Partial sprinkler system present",
    "No": "3 - No sprinkler system"
}

properties = ["All", "Residential", "Commercial", "Other"]

app = Dash(__name__)

app.layout = html.Div([

    html.Div([
        html.Div("Sprinkler System", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="sprinkler",
            options=[{"label": k, "value": k} for k in sprinklers.keys()],
            value="All"
        ),
    ], style={"width": "400px", "marginBottom": "10px"}),

    html.Div([
        html.Div("Property Type", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="property",
            options=[{"label": x, "value": x} for x in properties],
            value="All"
        ),
    ], style={"width": "400px", "marginBottom": "20px"}),

    dcc.Graph(id="graph")
])

def filter_df(s, p):
    d = df.copy()

    if s != "All":
        d = d[d["Sprinkler_System_Presence"] == sprinklers[s]]

    if p != "All":
        d = d[d["Property_Group_Plot"] == p]

    return d

@app.callback(
    Output("graph", "figure"),
    Input("sprinkler", "value"),
    Input("property", "value")
)
def update(s, p):

    dff = filter_df(s, p)

    color_vals = dff["Loss_Level"].map(loss_map)

    fig = go.Figure(
        go.Parcats(
            dimensions=[
                dict(label="Property", values=dff["Property_Group_Plot"]),
                dict(label="Sprinkler", values=dff["Sprinkler_System_Presence"]),
                dict(label="Scale", values=dff["Scale"]),
            ],
            line=dict(
                color=color_vals,
                colorscale=["#f8cdda", "#f06292", "#6a1b9a"],
                showscale=True,
                colorbar=dict(
                    title="Loss Level",
                    tickvals=[0, 1, 2],
                    ticktext=["Low", "Medium", "High"]
                )
            )
        )
    )

    fig.update_layout(
        margin=dict(l=80, r=80, t=20, b=20),
        height=600
    )

    return fig

if __name__ == "__main__":
    app.run(debug=True)