## Setup and Load

import pandas as pd
import geopandas as gpd
import numpy as np
import osmnx as ox
import networkx as nx
import os
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point

## Conveyal Helper Functions

def _any_cycle(r):
    # Creates an Overall Cycle Tag Based
    c = r['cycleway']
    co = r['cycleway_o']
    cb = r['cycleway_b']

    if (pd.notnull(c) and c != 'no') or (pd.notnull(co) and co != 'no') or (pd.notnull(cb) and cb != 'no'):
        return True
    else:
        return False

def _cycle_check(val):
    # Add cycle tag to edges
    if isinstance(val, list):
        return_val = False
        for v in val:
            if v in cycle_ids:
                return_val = True
        return return_val
    else:
        if val in cycle_ids:
            return True
        else:
            return False

def _speed_check(speeds):
    # Refactor Speed Variable
    if isinstance(speeds, list):
        all_speeds = []
        for speed in speeds:
            int_speed = int(speed.replace(' mph', '')) if pd.notnull(speed) else np.nan
            all_speeds.append(int_speed)
        return max(all_speeds)
    else:
        int_speed = speeds.replace(' mph', '') if pd.notnull(speeds) else np.nan
        int_speed = int(int_speed) if int_speed != '' and pd.notnull(int_speed) else np.nan
        return int_speed

def _lane_check(lanes):
    # Refactor Lane Variable
    if isinstance(lanes, list):
        all_lanes = []
        for lane in lanes:
            int_lane = int(lane) if pd.notnull(lane) else np.nan
            all_lanes.append(int_lane)
        return max(all_lanes)
    else:
        int_lane = int(lanes) if pd.notnull(lanes) else np.nan
#         int_lane = int(int_lane) if int_lane != '' and pd.notnull(int_lane) else np.nan
        return int_lane

def _conveyal_lts(r):
    road_type = r.highway
    speed = r.speed
    lanes = r.lane
    cycle = r.cycleTag

    if not isinstance(road_type, list):
        if road_type in exclude:
            return None
        elif road_type in no_cars:
            return 'LTS 1'
        elif road_type in low_level_cars:
            return 'LTS 1'
        elif speed < 25 and (pd.isna(lanes) or lanes < 4):
            return 'LTS 2'
        elif road_type in high_level_cars and (lanes < 4 or cycle == True):
            return 'LTS 2'
        elif cycle == True:
            return 'LTS 3'
        else:
            return 'LTS 4'

## Main Function

def add_lts(G, lts_method = 'conveyal', lts_threshold = 'LTS 2', output_method = 'preferred', preference_multiplier = 4):

    implemented_lts_methods = ['conveyal']
    lts_threshold = ["LTS 1", "LTS 2", "LTS 3", "LTS 4"]
    output_methods = ['preferred', 'exclusive']

    if lts_method not in implemented_lts_methods:
        raise Exception("Please select from the implemented LTS methods: {0}".format(', '.join(implemented_lts_methods)))

    if lts_threshold not in lts_levels:
        raise Exception("Please select from the following LTS levels: {0}".format(', '.join(lts_levels)))

    if output_method not in output_methods:
        raise Exception("Please select from the following output methods: {0}".format(', '.join(output_methods)))


    gdfs = ox.utils_graph.graph_to_gdfs(G)
    nodes, edges = gdfs

    if lts_method == 'conveyal':

        tc = ox.geometries_from_place('Denver, CO', tags = {'cycleway':True, 'cycleway:oneway' : True, 'cycleway:both' : True})
        keep_cols = ['geometry', 'bicycle', 'cycleway', 'cycleway:oneway', 'cycleway:both']
        tc[tc.geom_type == 'LineString'][keep_cols].to_file('cycleways')

        tc['cycleTag'] = tc.apply(_any_cycle, axis = 1)
        cycle_file = tc.query('cycleTag == True').copy()

        cycle_ids = cycle_file.osmid.unique()

        edges['cycleTag'] = edges.osmid.apply(_cycle_check)

        edges['speed'] = edges.maxspeed.apply(_speed_check)
        edges['lane'] = edges.lanes.apply(_lane_check)

        no_cars = ['cycleway', 'path', 'track', 'pedestrian']
        low_level_cars = ['residential', 'living_street']
        high_level_cars = ['unclassified', 'tertiary', 'tertiary_link']
        cars = ['primary', 'primary_link', 'secondary', 'secondary_link', 'trunk', 'trunk_link']
        exclude = ['service']

        edges['LTS'] = edges.apply(_conveyal_lts, axis = 1)
        edges['LTS'] = pd.Categorical(edges.LTS, categories = lts_levels, ordered = True)

    if output_method == 'preferred':
        edges['lts_length'] = edges.apply(lambda r: r.length * preference_multiplier if pd.notnull(r.LTS) and int(r.LTS[-1]) > int(lts_threshold[-1]) else r.length, axis = 1)
        edges.dropna(subset = ['LTS'], inplace = True)
    else:
        edges.query('LTS <= @lts_threshold', inplace = True)

    LTS_G = ox.utils_graph.graph_from_gdfs(nodes, edges)

    return LTS_G

