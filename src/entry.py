
import io
import json
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points
from pyproj import Geod
from js import Response
import data.ne_10m_coastline as coastline_zip

coastlines = gpd.read_file(io.BytesIO(bytes(coastline_zip)))
coastlines_geometry = coastlines['geometry'].unary_union

geod = Geod(ellps="WGS84")


def get_nearest_distance_location(coordinate, coastlines_geometry, geod):
    point = Point(coordinate['longitude'], coordinate['latitude'])
    nearest_geom = nearest_points(point, coastlines_geometry)

    angle1, angle2, distance = geod.inv(
        point.x, point.y, nearest_geom[1].x, nearest_geom[1].y
    )
    distance /= 1000  # Convert to kilometers

    return distance, coordinate, {
        'latitude': nearest_geom[1].y,
        'longitude': nearest_geom[1].x
    }


def generate_bing_maps_link(latitude, longitude, nearest_latitude, nearest_longitude):
    location_marker = f"{latitude}_{longitude}_Start"
    polyline_vertices = f"{latitude}_{longitude}_{nearest_latitude}_{nearest_longitude}"
    nearest_coast_marker = f"{nearest_latitude}_{nearest_longitude}_End"

    bing_maps_url = f"https://bing.com/maps/default.aspx?sp=point.{location_marker}~polyline.{polyline_vertices}~point.{nearest_coast_marker}"
    return bing_maps_url


async def on_fetch(request, env):
    try:
        body = await request.json()

        if 'coordinates' in body:
            coordinates = body['coordinates']
            results = []

            for coord in coordinates:
                distance, location, nearest_coast = get_nearest_distance_location(
                    coord, coastlines_geometry, geod
                )
                bing_maps_link = generate_bing_maps_link(
                    location['latitude'], location['longitude'],
                    nearest_coast['latitude'], nearest_coast['longitude']
                )
                result = {
                    "location": location,
                    "distance": distance,
                    "nearest_coast": nearest_coast,
                    "bing_maps_link": bing_maps_link
                }
                results.append(result)

            response = {"results": results}
        else:
            response = {"error": "Invalid request"}

        return Response.new(json.dumps(response), status=200, headers={"Content-Type": "application/json"})

    except Exception as e:
        return Response.new(json.dumps({"error": str(e)}), status=500, headers={"Content-Type": "application/json"})
