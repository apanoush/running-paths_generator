"""helper functions to find loops"""

import networkx as nx
import folium
from tqdm import tqdm
import numpy as np
from geopy.distance import geodesic
import random

def path_length_km(G, path):
    """computes the length of a path in kilometers"""
    dist = 0.0
    for i in range(len(path)-1):
        n1, n2 = path[i], path[i+1]
        p1 = (G.nodes[n1]['y'], G.nodes[n1]['x'])
        p2 = (G.nodes[n2]['y'], G.nodes[n2]['x'])
        dist += geodesic(p1, p2).km
    return dist

def find_loops(G, start_node, target_distance_km, num_attempts, tolerance, max_percentage_of_duplicate_nodes):
    """tries random loop paths around a node, return those near target distance"""
    random_nodes: set[tuple[int, int]] = set()
    loops = []
    nodes = list(G.nodes)

    for _ in tqdm(range(num_attempts), unit="path", desc="Trying new paths" ):
        # pick two random path nodes (within the computed radius)
        node1, node2 = np.random.choice(nodes, 2)
        if (node1, node2) in random_nodes:
            continue
        random_nodes.add((node1, node2))
        random_nodes.add((node2, node1))

        try:
            path1 = nx.shortest_path(G, start_node, node1, weight='length')
            path2 = nx.shortest_path(G, node1, node2, weight='length')
            path3 = nx.shortest_path(G, node2, start_node, weight='length')

            # prevent the 3 points from being aligned
            if (node1 in path3) or (node2 in path1):
                continue

            full_path = path1 + path2[1:] + path3[1:]

            len_path = len(full_path)
            len_path_without_duplicates = len(set(full_path))

            # avoid paths that have too much back and forth nodes
            if len_path_without_duplicates <= max_percentage_of_duplicate_nodes * len_path:
                continue

            d = path_length_km(G, full_path)

            if abs(d - target_distance_km) <= target_distance_km * tolerance:
                loops.append((full_path, d))
                tqdm.write(f"Found a new path of {d:.2f}km")

        except nx.NetworkXNoPath:
            continue
    return loops

def visualize_loops(G, loops, start_point):
    """render found loops on a Folium map with LayerControl toggles"""
    # picking "Cartodb Positron" (not default OSM) for better visiblity
    m = folium.Map(location=start_point, zoom_start=14, tiles="Cartodb Positron")

    # add start point marker
    folium.Marker(
        start_point,
        icon=folium.Icon(color="green", icon="play"),
        tooltip="Start Point"
    ).add_to(m)

    # add each loop as its own FeatureGroup so it can be toggled
    for i, (path, dist_km) in enumerate(loops, start=1):
        coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
        color = f"#{random.randint(0, 0xFFFFFF):06x}"

        # each loop in its own layer
        fg = folium.FeatureGroup(name=f"Loop {i}: {dist_km:.2f} km", show=False)

        folium.PolyLine(
            coords,
            color=color,
            weight=4,
            opacity=0.8,
            tooltip=f"Loop {i}: {dist_km:.2f} km"
        ).add_to(fg)

        fg.add_to(m)

    # add layer control to toggle visibility
    folium.LayerControl(collapsed=False).add_to(m)

    return m

def filter_similar_loops(loops, similarity_threshold=0.8):
    """filter out loops that share too many nodes (too similar)"""
    unique_loops = []
    seen = []

    for path, dist in loops:
        nodes = set(path)
        too_similar = False

        for prev_nodes in seen:
            intersection = len(nodes & prev_nodes)
            union = len(nodes | prev_nodes)
            sim = intersection / union if union else 0
            if sim > similarity_threshold:
                too_similar = True
                break

        if not too_similar:
            unique_loops.append((path, dist))
            seen.append(nodes)

    return unique_loops

