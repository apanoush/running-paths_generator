"""main script to run"""

import osmnx as ox
import pickle
import argparse
import os
import yaml
import sys
sys.path.insert(0, ".")
from src.loops import find_loops, visualize_loops, filter_similar_loops

parameters = yaml.safe_load(open("parameters.yaml", "r"))
settings = parameters["settings"]
START_POINT = tuple(settings["START_POINT"])
TARGET_DISTANCE_KM = settings["TARGET_DISTANCE_KM"]
TOLERANCE = settings["TOLERANCE"]
NUM_ATTEMPTS = settings["NUM_ATTEMPTS"]
MAX_PERCENTAGE_OF_DUPLICATE_NODES = settings["MAX_PERCENTAGE_OF_DUPLICATE_NODES"]
DISCARD_SIMILARITY_THRESHOLD = settings["DISCARD_SIMILARITY_THRESHOLD"]

RESULTS_PATH = parameters["paths"]["RESULTS_PATH"]

def main(args: argparse.Namespace) -> None:

    if args.coordinates:
        START_POINT = args.coordinates

    search_radius_m = (TARGET_DISTANCE_KM * (1+TOLERANCE)) * 1000 // 2 # radius for OSM data download
    search_radius_km = search_radius_m / 1000 

    filename_suffix = f"_{search_radius_km}km-around-{START_POINT}"

    # serialization of the OSM walking network
    # prevents code from re-downloading the map if already did with same parameters
    serialized_graph = os.path.join(RESULTS_PATH, f"osm_graph{filename_suffix}.pkl")
    if os.path.isfile(serialized_graph):
        print(f"Not downloading OSM walking network again, using '{serialized_graph}'")
        G = pickle.load(open(serialized_graph, "rb"))
    else:
        print(f"Downloading OSM walking network {search_radius_km}km around {START_POINT}...")
        G = ox.graph_from_point(START_POINT, dist=search_radius_m, network_type='walk')
        pickle.dump(G, open(serialized_graph, "wb"))

    print("Finding nearest node...")
    start_node = ox.distance.nearest_nodes(G, START_POINT[1], START_POINT[0])

    print(f"Searching for loops near {TARGET_DISTANCE_KM} km...")
    loops = find_loops(G, start_node, TARGET_DISTANCE_KM, num_attempts=NUM_ATTEMPTS, tolerance=TOLERANCE, max_percentage_of_duplicate_nodes=MAX_PERCENTAGE_OF_DUPLICATE_NODES)

    if not loops:
        print("No loops found within tolerance.")
        return

    if DISCARD_SIMILARITY_THRESHOLD:
        loops = filter_similar_loops(loops, DISCARD_SIMILARITY_THRESHOLD)

    print("Rendering map...")
    m = visualize_loops(G, loops, START_POINT)
    map_filename = os.path.join(RESULTS_PATH, f"running_loops_map{filename_suffix}.html")
    m.save(map_filename)
    print(f"Map saved as '{map_filename}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="running-paths_generator", description="Generates multiple paths around a choosen starting point")
    # adding a coordinates argument that takes exactly two floats
    parser.add_argument(
        "--coordinates", "-c",
        type=float,
        nargs=2,
        metavar=("LAT", "LON"),
        help="Specify coordinates as two floats: latitude and longitude (separated by a space)."
    )
    args = parser.parse_args()
    main(args)
