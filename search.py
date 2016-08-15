"""
I was using a dataset collected by myself from booking.com
I was crawling search pages for cities in the US (dest_id from 20000001 to 20154800, search uri is "http://www.booking.com/searchresults.en-gb.html?dest_type=city&dest_id=#dest_id#”.
I’ve selected destinations with reasons to visit (around 3000 cities in the end).
For those 3K cities I had the following information: city_id, city_name, number of hotels in the city,  reasons to visit, location(lat, lon) of one of the city hotels, the hotel address and url.
I was using this data for the prototype I’ve created.
The dataset (as well as this file) can be downloaded from GitHub:
https://github.com/mavlyutovrus/booking_challenge

I assume that one person can recommend several attractions/passions in one city.

Strength of passion satisfaction

The provided data doesn’t allow directly estimate the strength of passion satisfaction (for that goal it is better to have per-reviewer recommendations with the information about the reviewers passions).
I see at least 4 factors that can have an impact to the amount of recommendations for a certain passion  in a certain city (RecCnt(C, P)):
1) city popularity (Popularity(C)) - amount of people visiting the city;
2) passion popularity (Popularity(P)) - amount of people having passion P ;
3) strength with which the passion can be satisfied in the city (Satisfaction(P, C));
4) Time of the statistics collection (assume the same for all cities here)
Having this in mind let's assume the following dependency:

Pop(C) * Pop(P) * Sat(P, C) ~ RecCnt(C, P)

Pop(C) can be estimated by the amount of hotels in the city:
Pop(C) ~ Hotels(C)

Pop(P) can be estimated by the amount of users who have that passion
Pop(P) ~ UsersThatHave(P)
However, we don’t have this data, so I will assume that this value is proportional to the amount of cities where this passion was recommended (which is of course quite doubtful assumption):
Pop(P) ~ CitiesThatHave(P)

Having this dependencies we can estimate the strength of the passion satisfaction:

Sat(P,C) ~ RecCnt(C, P) / (MAX([RecCnt(C,P) for all P]) * CitiesThatHave(P))

Answering a query

Query = [P1..Pn] - a list of passions.

Not all passions are equal. I could try to make up a priority order basing on passions selectivity,  though I think it is up to a user to decide what is more important for her.
A user can define her priorities by the order of passions in a query.

So the first formula to sum up the relevance of a city to a query would be:

Relevance(Q, C) = SUM([Sat(P,C) / ln(e + IndexOfPinQ)  for all P in Q])

I would like to elaborate this formula a bit, since often there are several cities nearby, and one city can leverage positive sides of another.
To take this into account I will introduce another Satisfaction function:

Sat*(P,C) = MAX([Sat(P,Cn) * DistancePenalty(C, Cn) for all Cn in neighbourhood of C]

Cn in neighbourhood of C is any city that is in 50km (let's say) from C.

DistancePenalty(C, Cn) =  1 / ( 1 + MIN(Distance(C, Cn), MAX_NEIGHBOUR_DISTANCE) / MAX_NEIGHBOUR_DISTANCE )

Sat*(P,C) should be precalculated for any pair (P,C) that have Sat*(P,C) value more than 0.

Final formula for city relevance:
Relevance(Q, C) = SUM([Sat*(P,C) / ln(e + IndexOfPinQ)  for all P in Q])

Notes/Ideas:

1) Ideally all this formulas should be parametrised.
The optimal set of values for the parameters should be found by using a training set of queries with cities' relevances.

2) Outliers, like joking recommendations will be filtered out, since they will have lower frequencies comparing to legit recommendations.

3) I did not have the original dataset, so it didn't make sense to clusterize the passions.
However in case of the raw data (city -> passion -> recommendations count) it definitely should be done. We could expect copious variations of names for some passions, as well as highly related terms like (“nature”, “scenery”), (“lake”, “fishing”), etc.
I would use word2vec to build relations between the terms. Words similarities and linguistic tools like WordNet may also help. We can expect no more that several hundreds of frequent terms, so the ontology can be build even manually.

Having relations between terms may help for several reasons.
If we have several highly-related terms in a query (like "nature" and "mountain" or "mountains" and "scenery")  may overweight their importance comparing to the other query terms (like in the query ["nature", "mountains", "wine"], where "mountains" will be supported by "nature" and highly overweight "wine").
Relations between terms might also help to extend the search query with additional terms (like adding “scenery” to “mountains”).

"""




from math import radians, cos, sin, asin, sqrt

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

MAX_NEIGHBOUR_LAT_DISTANCE  = 2 #degrees
MAX_NEIGHBOUR_LON_DISTANCE  = 10 #degrees
MAX_NEIGHBOUR_DISTANCE = 50 # km
DISTANCE_PENALTY = 2


class TSearch(object):

    def __init__(self):
        self.city2geo_location = {}
        self.city2name = {}
        self.city2recomms = {}
        self.ciyt2hotels_count = {}
        self.city_passion_satisfaction = {}
        print "..uploading"
        for line in open("cities_data.txt"):
            code, city_path, city_hotels_count, recommendations, lat, lon, one_hotel_address, hotel_page = \
                                                                                          line.strip().split("\t")
            code = int(code)
            city_hotels_count = int(city_hotels_count)
            recommendations = recommendations.split(";")
            lat, lon = float(lat), float(lon)
            self.city2geo_location[code] = (lat, lon)
            self.city2name[code] = city_path
            self.city2recomms[code] = recommendations
            self.ciyt2hotels_count[code] = city_hotels_count
        cities = self.city2geo_location.keys()

        #number of cities where the recommendation was mentioned ~ passion popularity
        recommendations2city_count = {}
        for city in cities:
            for recomm in self.city2recomms[city]:
                recommendations2city_count.setdefault(recomm, 0)
                recommendations2city_count[recomm] += 1
        #max recomm freq for a city (we don't have this data
        print "..calculating local satisfactions"
        local_satifactions = {}
        for city in cities:
            local_satifactions.setdefault(city, {})
            for recomm in self.city2recomms[city]:
                import random
                random.seed(0)
                # we don't have this data, so fake it
                recomm_count =  (random.random() + 1)* 0.5 * 10 * self.ciyt2hotels_count[city]
                statisfaction = float(recomm_count) / (recommendations2city_count[recomm] * self.ciyt2hotels_count[city])
                local_satifactions[city][recomm] = statisfaction
        self.local_satifactions = local_satifactions
        print "..calculating city neighbours"
        #city_neighbours = self.calc_city_neighbours() # TODO: elaborate
        city_neighbours = self.calc_city_neighbours_simple(cities)
        print "..calculating global satisfactions"
        self.satifactions_with_neighbourhood = {}
        for city in cities:
            neighbourhood = [(city, 0)] # (city_id, distance)
            if city in city_neighbours:
                neighbourhood += city_neighbours[city]
            max_satisfactions = {}
            for neigh_city, distance in neighbourhood:
                for recomm, local_satisfaction in local_satifactions[neigh_city].items():
                    distant_satisfaction = local_satisfaction / (1.0 +  DISTANCE_PENALTY * float(distance) /
                                                                                                MAX_NEIGHBOUR_DISTANCE)
                    max_satisfactions.setdefault(recomm, 0)
                    max_satisfactions[recomm] = max(distant_satisfaction, max_satisfactions[recomm])
            self.satifactions_with_neighbourhood[city] = max_satisfactions
        print "..reverse index: recomm -> cities"
        self.recomm2city = {}
        for city, city_satisfactions in self.satifactions_with_neighbourhood.items():
            for recomm in city_satisfactions.keys():
                self.recomm2city.setdefault(recomm, []).append(city)
        print "recommendations with freqs;",  [(recomm, len(cities)) for recomm, cities in self.recomm2city.items()]
        print "..all indices created"


    def query(self, preferences):
        import math
        city2score = {}
        for recomm_index in xrange(len(preferences)):
            recomm = preferences[recomm_index]
            # earlier in the list -> more important
            user_recomm_weight = 1.0 / math.log(2 + recomm_index, 2)
            if recomm in self.recomm2city:
                for city in self.recomm2city[recomm]:
                    city2score.setdefault(city, 0)
                    city2score[city] += self.satifactions_with_neighbourhood[city][recomm] * user_recomm_weight
        by_score =[(score, city) for city, score in city2score.items()]
        by_score.sort(reverse=True)
        #for score, city in by_score[:10]:
        #    print score, self.city2name[city], self.local_satifactions[city].items()
        #    print self.satifactions_with_neighbourhood[city].items()
        return [(score, self.city2name[city]) for score, city in by_score[:10]]

    def calc_city_neighbours_simple(self, cities):
        city_neighbours = {}
        pairs = 0
        for first_city_index in xrange(len(cities)):
            first_city = cities[first_city_index]
            first_lat, first_lon = self.city2geo_location[first_city]
            for second_city_index in xrange(first_city_index + 1, len(cities)):
                second_city = cities[second_city_index]
                second_lat, second_lon = self.city2geo_location[second_city]
                if abs(first_lat - second_lat) > MAX_NEIGHBOUR_LAT_DISTANCE:
                    continue
                if abs(first_lon - second_lon) > MAX_NEIGHBOUR_LON_DISTANCE:
                    continue
                distance = haversine(first_lat, first_lon, second_lat, second_lon)
                if distance > MAX_NEIGHBOUR_DISTANCE:
                    continue
                pairs += 1
                city_neighbours.setdefault(first_city, []).append((second_city, distance))
                city_neighbours.setdefault(second_city, []).append((first_city, distance))
        #print pairs
        return city_neighbours

    def calc_city_neighbours(self):
        city_neighbours = {}
        by_quadrant = {}
        for city, location in self.city2geo_location.items():
            lat, lon = location
            y = int(lat / MAX_NEIGHBOUR_LAT_DISTANCE)
            x = int(lon / MAX_NEIGHBOUR_LON_DISTANCE)
            for y_assign in xrange(y - 1, y + 2):
                for x_assign in xrange(x - 1, x + 2):
                    by_quadrant.setdefault((y_assign, x_assign), []).append(city)
        pairs = set()
        for quadrant_cities in by_quadrant.values():
            for first_city_index in xrange(len(quadrant_cities)):
                first_city = quadrant_cities[first_city_index]
                first_lat, first_lon = self.city2geo_location[first_city]
                for second_city_index in xrange(first_city_index + 1, len(quadrant_cities)):
                    second_city = quadrant_cities[second_city_index]
                    second_lat, second_lon = self.city2geo_location[second_city]
                    if abs(first_lat - second_lat) > MAX_NEIGHBOUR_LAT_DISTANCE:
                        continue
                    if abs(first_lon - second_lon) > MAX_NEIGHBOUR_LON_DISTANCE:
                        continue
                    pair = (min(first_city, second_city), max(first_city, second_city))
                    if pair in pairs:
                        continue
                    distance = haversine(first_lat, first_lon, second_lat, second_lon)
                    if distance > MAX_NEIGHBOUR_DISTANCE:
                        continue
                    pairs.add(pair)
                    city_neighbours.setdefault(first_city, []).append((second_city, distance))
                    city_neighbours.setdefault(second_city, []).append((first_city, distance))
        #print len(pairs)
        return city_neighbours

search = TSearch()
query = ["nature", "restaurants"]
search_results = search.query(query)
for result in search_results:
    print result
