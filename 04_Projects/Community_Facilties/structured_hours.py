import re
from datetime import datetime

def parse_time_range(time_str):
    """Convert time range like '11:00 A.M - 3:00 P.M' to {'open': '11:00', 'close': '15:00'} in 24h format."""
    if pd.isnull(time_str):
        return None
    try:
        parts = re.split(r'\s*-\s*', time_str.strip())
        if len(parts) != 2:
            return None
        open_ = datetime.strptime(parts[0], "%I:%M %p").strftime("%H:%M")
        close_ = datetime.strptime(parts[1], "%I:%M %p").strftime("%H:%M")
        return {"open": open_, "close": close_}
    except Exception:
        return None

# Rebuild GeoJSON with structured time format
features_structured = []
for _, row in df.iterrows():
    if pd.notnull(row['Lat']) and pd.notnull(row['Long']):
        hours = {}
        for day in day_columns:
            hours[day] = parse_time_range(row.get(day))
        
        properties = {
            "name": row['Name of Garden'],
            "address": row['Address/ Location'],
            "hours": hours
        }
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row['Long'], row['Lat']]
            },
            "properties": properties
        }
        features_structured.append(feature)

geojson_structured = {
    "type": "FeatureCollection",
    "features": features_structured
}

# Save to file
structured_output_path = "/mnt/data/Community_Gardens_Structured_Hours.geojson"
with open(structured_output_path, "w") as f:
    json.dump(geojson_structured, f, indent=2)

structured_output_path
