## OSMNX Bike Level of Traffic Stress Integration

This script surrounds one primary function - add_lts - which calculates the bike level of traffic stress (LTS) for all edges in a networkx graph and calculates a new length (cost) column based on a users LTS threshold for use in shortest path and other network calculations.

### BLTS Classification Methods
Currently, the only method for calculating BLTS is based on the [Conveyal Method](https://docs.conveyal.com/learn-more/traffic-stress) which uses only the most basic OSM tags and makes more assumptions about the road.

I am working on functions that use more OSM tags and are closer to the original [Mineta Institute Bike LTS Calculations](https://transweb.sjsu.edu/research/low-stress-bicycling-and-network-connectivity)

### LTS Threshold Calculations
There are two ways to use the LTS threshold:

1. **"exclusive"** - this returns a graph that has EXCLUSIVELY edges that are within the LTS threshold. This means if there is no route that exclusively uses roads under the LTS threshold, no route will be returned. Useful for examining the extent of BLTS accessibility or for users that will not go on a LTS level higher than their comfort rating even for short distances.

2. **"preferred"** - this returns all edges in the graph, but heavily disincentivizes edges that are above the LTS threshold based on the preference_multiplier. The preference_multiplier is how far out of their way someone is willing to go to avoid a road above their LTS threshold (i.e. a value of 4 (default) means they would prefer to go 4x the distance on a particular section of the route rather than go on a higher LTS road). A preference_multiplier of 1 is the same as using direct route calculations. There is no upper limit on the preference_multiplier but anything beyond a 10 and you should probably be using the "exclusive" route calculation.

![[LTS Threshold Examples]](example.png)

### Specifics
```
add_lts(G, lts_method = 'conveyal', lts_threshold = 'LTS 2', output_method = 'preferred', preference_multiplier = 4)

G <--------------------- (networkx.MultiDiGraph) input graph
lts_method <------------ (str) How to calculate LTS for each edge: conveyal (default)
lts_threshold <--------- (str) The LTS level a user is comfortable with
output_method <--------- (str) preferred (default) or exclusively routes equal to or under the lts_threshold
preference_multiplier <- (int) how heavily to weight edges above the lts_threshold


Returns <---------------- an OSMNX NetworkX Graph with a new column lts_length
                          the lts_length column can be used as the weight in
                          any NetworkX of OSMNX network calculations.
                          "preferred" returns all edges in the original
                          "exclusive" returns only edges below the lts_threshold
```
