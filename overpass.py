import pandas as pd
import geopandas as gpd
import requests
import json
import osmnx as ox
import numpy as np
import os
import re
from math import ceil
import matplotlib.pyplot as plt

## create overpass function
def overpass(polygon, year, qtype):
    minx, miny, maxx, maxy = polygon.total_bounds

    overpass_url = "http://overpass-api.de/api/interpreter"
    # overpass_url = "//overpass-api.de/api/"
    way_query = """
    [date:"{year}-01-01T00:00:00Z"][out:json];
    way({miny}, {minx}, {maxy}, {maxx})->.all;
    (
    way.all["cycleway"];
    way.all["cycleway:left"];
    way.all["cycleway:left:width"];
    way.all["cycleway:right"];
    way.all["cycleway:right:width"];
    way.all["cycleway:both"];
    way.all["cycleway:both:width"];
    way.all["cycleway:buffer"];
    way.all["cycleway:left:buffer"];
    way.all["cycleway:right:buffer"];
    way.all["cycleway:both:buffer"];
    way.all["footway"];
    way.all["highway"];
    way.all["maxspeed"];
    way.all["lanes:forward"];
    way.all["lanes:backward"];
    way.all["lanes:both_ways"];
    way.all["oneway"];
    way.all["oneway:bicycle"];
    way.all["parking:lane:right"];
    way.all["parking:lane:right:width"];
    way.all["parking:lane:left"];
    way.all["parking:lane:left:width"];
    way.all["parking:lane:both"];
    way.all["parking:lane:both:width"];
    way.all["turn:lanes:both_ways"];
    way.all["turn:lanes:backward"];
    way.all["turn:lanes:forward"];
    way.all["width"];
    );
    out;
    """.format(year = year, miny = miny, minx = minx, maxy = maxy, maxx = maxx)

    node_query = """
    [date:"{year}-01-01T00:00:00Z"][out:json];
    node({miny}, {minx}, {maxy}, {maxx})->.all;
    (
        node.all["flashing_lights"];
        node.all["button_operated"];
        node.all["crossing"];
    );
    out;
    """.format(year = year, miny = miny, minx = minx, maxy = maxy, maxx = maxx)

    if qtype == 'way':
        response = requests.get(overpass_url,
                            params={'data': way_query})
    elif qtype == 'node':
        response = requests.get(overpass_url,
                            params={'data': node_query})
    else:
        raise Exception("Not an accepted value for qtype")

    data = response.json()
    df = pd.DataFrame(data["elements"])

    return df

## pull overpass data

polygon = gpd.read_file('untitled_map.geojson')
year = 2020
way = overpass(polygon, year, qtype = 'way')
node = overpass(polygon, year, qtype = 'node')

## convert tags to individual columns

for idx, val in way.iterrows():
    tags = val['tags']
    for key in tags.keys():
        way.loc[idx, key] = tags[key]


for idx, val in node.iterrows():
    tags = val['tags']
    for key in tags.keys():
        node.loc[idx, key] = tags[key]

## Read saved files - for debug

# way.to_csv('way')
# node.to_csv('node')

way = pd.read_csv('way')
node = pd.read_csv('node')

# add missing columns if missing
for col in ['parking:lane:right:width', 'parking:lane:left:width', 'parking:lane:both:width', 'cycleway:left:buffer', 'cycleway:right:buffer', 'cycleway:both:buffer', 'cycleway:left:width', 'cycleway:right:width', 'cycleway:both:width']:
    if col not in way.columns:
        way[col] = np.nan

way = way.copy()
node = node.copy()


## collapse list highways to single

highway_order = ['motorway',
    'motorway_link',
    'trunk',
    'trunk_link',
    'primary',
    'primary_link',
    'secondary',
    'secondary_link',
    'tertiary',
    'tertiary_link',
    'unclassified',
    'residential',
    'path',
    'living_street']

#     'service',
#     'track'

min_val = lambda h: highway_order[min([highway_order.index(hh) for hh in h])]
way['h2'] = way.highway.apply(lambda t: minval if type(t) == list else t)

way.query('h2 in @highway_order', inplace = True)

# clean speed
reg = re.compile(r'\d+')
way['maxspeed'] = way['maxspeed'].apply(lambda s: int(re.findall(reg, s)[0]) if pd.notnull(s) else s)

# clean lanes
way['lanes:forward'] = way['lanes:forward'].astype(float)
way['lanes:backward'] = way['lanes:backward'].astype(float)
way['lanes:both_ways'] = way['lanes:both_ways'].astype(float)

def left_right_num(r, base, t):
    if t == 'lr':
        tr = 'right'
        tl = 'left'
        tb = 'both'
    else:
        tr = 'forward'
        tl = 'backward'
        tb = 'both_ways'

    if pd.isna(r[base.format(tl)]) and pd.isna(r[base.format(tr)]) and pd.notna(r[base.format(tb)]):
        lcount = r[base.format(tb)] / 2
        return lcount, lcount
    else:
        return r[base.format(tl)], r[base.format(tr)]

def left_right_cat(r, base):
    if pd.isna(r[base.format('left')]) and pd.isna(r[base.format('right')]) and pd.notna(r[base.format('both')]):
        return r[base.format('both')], r[base.format('both')]
    else:
        return r[base.format('left')], r[base.format('right')]

way[['lanes:forward', 'lanes:forward']] = way.apply(left_right_num, args = ['lanes:{}', 'fb'], axis = 1, result_type = 'expand')

# clean bike lanes
way['cycleway:both'] = way.apply(lambda r: r['cycleway'] if pd.notnull(['cycleway:both']) and r['cycleway'] != 'crossing' else r['cycleway:both'], axis = 1)
way[['cycleway:left', 'cycleway:right']] = way.apply(left_right_cat, args = ['cycleway:{}'], axis = 1, result_type = 'expand')

# clean widths and buffers
way[['cycleway:left:width', 'cycleway:right:width']] = way.apply(left_right_cat, args = ['cycleway:{}:width'], axis = 1, result_type = 'expand')
way[['cycleway:left:buffer', 'cycleway:right:buffer']] = way.apply(left_right_cat, args = ['cycleway:{}:buffer'], axis = 1, result_type = 'expand')

# clean parking
way[['parking:lane:left', 'parking:lane:right']] = way.apply(left_right_cat, args = ['parking:lane:{}'], axis = 1, result_type = 'expand')
way[['parking:lane:left:width', 'parking:lane:right:width']] = way.apply(left_right_num, args = ['parking:lane:{}:width', 'lr'], axis = 1, result_type = 'expand')

## LTS Classifier

def sum_na(s):
    return s.isna().sum() / len(s)

def_table_num = way.groupby('h2').agg('median')
def_table_cat = way.groupby('h2').agg(pd.Series.mode)

def_nas = way.groupby('h2').agg(sum_na)
max_na = .2

set_def = {'h': ['primary',
            'primary_link',
            'secondary',
            'secondary_link',
            'tertiary',
            'tertiary_link',
            'unclassified',
            'residential'],
            'speed': [40, 40, 40, 40, 30, 30, 25, 25],
            'lanes': [2, 2, 2, 2, 1, 1, 1, 1],
            'parking': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'],
            'parking_width': [8, 8, 8, 8, 8, 8, 8, 8],
            'buffered_bike_width': [6, 6, 6, 6, 6, 6, 6, 6],
            'bike_width_park': [5, 5, 5, 5, 5, 5, 5, 5],
            'bike_width_nopark': [4, 4, 4, 4, 4, 4, 4, 4]}

set_def_table = pd.DataFrame(set_def)
set_def_table.set_index('h', inplace = True)

def num_defaults(h, r, col):
    val = r[col]
    if pd.isna(val) and def_nas.loc[h, col] < max_na:
        ret_val = def_table_num.loc[h, col]
        return ceil(ret_val) if pd.notnull(ret_val) else np.nan
    else:
        return val

def cat_defaults(h, r, col):
    val = r[col]
    if pd.isna(val) and def_nas.loc[h, col] < max_na:
        ret_val = def_table_cat.loc[h, col]
        return ret_val
    else:
        return val

def lts_classifier(r, direction):
    if direction == 'right':
        lane_direction = 'forward'
    else:
        lane_direction = 'backward'

    # highway type
    h = r.h2

    lts = []

    if h in ['motorway', 'motorway_link', 'trunk', 'trunk_link']:
        return 5

    elif h in ['path', 'living_street']:
        return 1

    else:
        # classifiers
        bike = cat_defaults(h, r, f'cycleway:{direction}')

        park = cat_defaults(h, r, f'parking:lane:{direction}')
        park =  set_def_table.loc[h, 'parking'] if pd.isna(park) else park

        # lanes and speed
        lanes = num_defaults(h, r, f'lanes:{lane_direction}')
        lanes =  set_def_table.loc[h, 'lanes'] if pd.isna(lanes) else lanes

        speed = num_defaults(h, r, f'maxspeed')
        speed =  set_def_table.loc[h, 'speed'] if pd.isna(speed) else speed

        # widths
        cycle_width = num_defaults(h, r, f'cycleway:{direction}:width')

        if park in ['Y', 'parallel', 'diagonal', 'perpendicular']:
            cycle_width =  set_def_table.loc[h, 'bike_width_park'] if pd.isna(cycle_width) else cycle_width
            if pd.notnull(r[f'cycleway:{direction}:buffer']) and r[f'cycleway:{direction}:buffer'] != 'no':
                cycle_width += 1
        else:
            cycle_width =  set_def_table.loc[h, 'bike_width_nopark'] if pd.isna(cycle_width) else cycle_width
            if pd.notnull(r[f'cycleway:{direction}:buffer']) and r[f'cycleway:{direction}:buffer'] != 'no':
                cycle_width += 2

        park_width = cycle_width + num_defaults(h, r, f'parking:lane:{direction}:width')

        if bike in ['lane', 'track']:

            # BIKE LANE AND PARKING
            if park in ['Y', 'parallel', 'diagonal', 'perpendicular']:
                # lanes
                if lanes <= 2:
                    lts.append(1)
                else:
                    lts.append(3)

                # speed
                if speed <= 25:
                    lts.append(1)
                elif speed <= 30:
                    lts.append(2)
                elif speed <= 35:
                    lts.append(3)
                else:
                    lts.append(4)

                # width
                if park_width >= 15:
                    lts.append(1)
                elif park_width >= 14.5:
                    lts.append(2)
                elif park_width > 13.5:
                    lts.append(3)
                else:
                    lts.append(4)

            # BIKE LANE
            else:
                # lanes
                if lanes == 1:
                    lts.append(1)
                else:
                    lts.append(3)

                # speed
                if speed <= 30:
                    lts.append(1)
                elif speed <= 35:
                    lts.append(3)
                else:
                    lts.append(4)

                # width
                if cycle_width >= 6:
                    lts.append(1)
                else:
                    lts.append(2)
        else:

            # MIXED TRAFFIC
            if lanes <= 3:
                if speed <= 25:
                    if h == 'residential' and lanes < 3:
                        lts.append(1)
                    else:
                        lts.append(2)
                elif speed <= 30:
                    if h == 'residential' and lanes < 3:
                        lts.append(2)
                    else:
                        lts.append(3)
                else:
                    lts.append(4)
            elif lanes <= 5:
                if speed <= 25:
                    lts.append(3)
                else:
                    lts.append(4)
            else:
                lts.append(4)

    return max(lts) if len(lts) != 0 else np.nan

## Run LTS

way['lts_right'] = way.apply(lts_classifier, args = ['right'], axis = 1)
way['lts_left'] = way.apply(lts_classifier, args = ['left'], axis = 1)

way['LTS'] = way[['lts_right', 'lts_left']].max(axis = 1)

poly = polygon.iloc[0].geometry

G = ox.graph.graph_from_polygon(poly, network_type = 'all')

gdfs = ox.utils_graph.graph_to_gdfs(G)
nodes, edges = gdfs

way_join = way[['id', 'LTS']].copy().to_dict('split')['data']
wj = {d[0] : d[1] for d in way_join}

def lts_merge(i):
    if type(i) != list:
        if i in wj.keys():
            return wj[i]
        else:
            return np.nan
    else:
        wjl = [wj[ii] for ii in i if ii in wj.keys()]
        return max(wjl) if len(wjl) > 0 else np.nan

edges['LTS'] = edges.osmid.apply(lts_merge)
edges['LTS'] = edges.LTS.apply(lambda s: 'LTS {0}'.format(int(s)) if pd.notna(s) else np.nan)

lts_thresholds = ["LTS 1", "LTS 2", "LTS 3", "LTS 4", "LTS 5"]
lts_threshold = "LTS 2"
edges['LTS'] = pd.Categorical(edges.LTS, categories = lts_thresholds, ordered = True)

edges.plot(column = 'LTS', cmap = 'coolwarm',  legend = True)
plt.show()


output_method = 'exclusive'

if output_method == 'preferred':
    edges['lts_length'] = edges.apply(lambda r: r.length * preference_multiplier if pd.notnull(r.LTS) and int(r.LTS[-1]) > int(lts_threshold[-1]) else r.length, axis = 1)
    edges.dropna(subset = ['LTS'], inplace = True)
else:
    edges.query('LTS <= @lts_threshold', inplace = True)

LTS_G = ox.utils_graph.graph_from_gdfs(nodes, edges)


