import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import warnings
from streamlit_folium import st_folium

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")
st.title("NYC Heat Vulnerability & Cooling Access Map")


# Load datasets

@st.cache_data
def load_data():
    # Using correct filenames from earlier cells
    cooling = pd.read_csv("Cool_It!_NYC_2020_-_Cooling_Sites_20260202.csv")
    trees = pd.read_csv("2015_Street_Tree_Census_-_Tree_Data_20260202.csv")
    acs = pd.read_csv("ACSDT5YAIAN2021.B11007-2026-02-02T125333.csv")

    cooling.columns = cooling.columns.str.strip().str.lower()
    trees.columns = trees.columns.str.strip().str.lower()

    # clean coordinates
    cooling['x'] = cooling['x'].str.replace(',', '').astype(float)
    cooling['y'] = cooling['y'].str.replace(',', '').astype(float)

    cooling_gdf = gpd.GeoDataFrame(
        cooling,
        geometry=gpd.points_from_xy(cooling['x'], cooling['y']),
        crs="EPSG:2263"
    ).to_crs(4326)

    # trees
    trees = trees.dropna(subset=['latitude', 'longitude'])
    trees_gdf = gpd.GeoDataFrame(
        trees,
        geometry=gpd.points_from_xy(trees['longitude'], trees['latitude']),
        crs="EPSG:4326"
    )

    # Identifying the correct census tract column
    tract_col = [c for c in trees_gdf.columns if 'tract' in c][0]
    tree_density = (
        trees_gdf
        .groupby(tract_col)
        .size()
        .reset_index(name="tree_count")
    )

    # ACS cleanup
    acs.columns = acs.columns.str.strip()
    acs['GEOID'] = acs.iloc[:, 0].astype(str)
    acs['tract_2010'] = acs['GEOID'].str[-6:]

    analysis_df = acs.merge(
        tree_density,
        left_on='tract_2010',
        right_on=tract_col,
        how='left'
    )

    analysis_df['tree_count'] = analysis_df['tree_count'].fillna(0)

    return cooling_gdf, analysis_df

cooling_gdf, analysis_df = load_data()

# ---------------------------
# Create buffer
# ---------------------------
buffer_gdf = cooling_gdf.to_crs(2263)
buffer_gdf['buffer'] = buffer_gdf.geometry.buffer(800)
buffer_gdf = buffer_gdf.set_geometry('buffer').to_crs(4326)

# ---------------------------
# Map
# ---------------------------
m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)

# Cooling points
for _, row in cooling_gdf.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=3,
        color='blue',
        fill=True
    ).add_to(m)

import json

# Convert buffer GeoDataFrame to safe GeoJSON
buffer_geojson = json.loads(buffer_gdf.to_json())

folium.GeoJson(
    buffer_geojson,
    style_function=lambda x: {
        'fillColor': 'blue',
        'color': 'blue',
        'weight': 1,
        'fillOpacity': 0.15
    },
    name="Cooling Access Buffer"
).add_to(m)

st.subheader("Cooling Acc



# Summary stats

st.subheader("Tree Density Summary")

st.metric("Total Census Tracts", len(analysis_df))
st.metric("Average Trees per Tract", round(analysis_df['tree_count'].mean(), 2))

st.dataframe(analysis_df[['tract_2010', 'tree_count']].head(10))


# Risk Index

analysis_df['risk_index'] = (
    analysis_df['tree_count'].rank(pct=True)
)

priority = analysis_df[analysis_df['risk_index'] < 0.25]

st.subheader("High Risk Priority Tracts")
st.write("Tracts with lowest tree density (proxy for heat vulnerability)")
st.dataframe(priority[['tract_2010', 'tree_count']])
