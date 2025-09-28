import json
import geopandas as gpd
from shapely.geometry import shape

COLONIAS_FILE = "catlogo-de-colonias.json"

with open(COLONIAS_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

# Asegurarnos que tenga features
features = raw["features"]

# Convertir cada feature en registro con props + geometry
rows = []
for ft in features:
    props = ft["properties"]
    geom = shape(ft["geometry"])
    props["geometry"] = geom
    rows.append(props)

# Crear GeoDataFrame
gdf_colonias = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
print("Columns in colonias file:", gdf_colonias.columns)
print(gdf_colonias.head())

print(gdf_colonias.columns)
print(gdf_colonias.head())
