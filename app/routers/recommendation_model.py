import os
from typing import List

import pandas as pd
from dotenv import load_dotenv
from mlxtend.frequent_patterns import apriori
from sqlalchemy.orm import Session

from app.models import Trips, User
from app.routers.discover import get_nearby_places_from_api

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


def get_travel_group_preferences(trip_id: int, db: Session) -> pd.DataFrame:
    """
    Get the preferences of the travel group.

    :param db: Database session.
    :param trip_id: The ID of the trip.
    :return: DataFrame containing UserId and Preferences columns.
    """
    # Get the companion IDs
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()
    companions = trip.companion.split(",") if trip.companion else []
    companions += [trip.owner]  # Add the owner to the travel group

    # Get the preferences of the travel group
    travel_group_preferences = (
        db.query(User).filter(User.username.in_(companions)).all()
    )

    # Convert to DataFrame with correct structure
    travel_group_preferences_df = pd.DataFrame(
        [
            {"UserId": user.username, "Preferences": user.preferences}
            for user in travel_group_preferences
        ]
    )

    return travel_group_preferences_df


def one_hot_encode_preferences(travel_group: pd.DataFrame):
    expanded_preferences = (
        travel_group["Preferences"]
        .str.split(",", expand=True)
        .stack()
        .reset_index(level=1, drop=True)
    )
    expanded_preferences.name = "AttractionType"

    unique_attractions = expanded_preferences.unique()
    one_hot = pd.DataFrame(0, index=travel_group.index, columns=unique_attractions)

    for idx, row in travel_group.iterrows():
        preferences = row["Preferences"].split(",")
        for pref in preferences:
            one_hot.at[idx, pref] = 1

    return one_hot


def extract_group_profile(encoded_travel_group: pd.DataFrame) -> pd.DataFrame:
    if len(encoded_travel_group) > 1:
        min_support = 2 / len(encoded_travel_group)
        frequent_itemsets = apriori(
            encoded_travel_group, min_support=min_support, use_colnames=True
        )
        frequent_size_one = frequent_itemsets[
            frequent_itemsets["itemsets"].apply(len) == 1
            ]
        return frequent_size_one
    else:
        preferences = list(encoded_travel_group.columns)
        data = {
            "support": [1.0] * len(preferences),
            "itemsets": [{pref} for pref in preferences],
        }
        group_profile = pd.DataFrame(data)
        return group_profile


async def get_nearby_destinations(lat: float, lon: float) -> pd.DataFrame:
    """
    Get nearby places from Google Places API (Nearby Search).
    :param lat: Latitude
    :param lon: Longitude
    :return: List of nearby places
    """
    g_fields = 'places.id,places.displayName,places.types'
    response = await get_nearby_places_from_api(g_fields, lat, lon, 20, 8000)

    nearby_places_df = pd.DataFrame(
        [
            {
                "AttractionId": place.get('id'),
                "Attraction": place.get('displayName')["text"],
                "AttractionType": ",".join(place.get('types'))  # Convert list of types to comma-separated string
            }
            for place in response.get("places", [])
        ]
    )

    return nearby_places_df


def get_suitable_destinations(destinations: pd.DataFrame, group_profile: List) -> pd.DataFrame:
    # Encode attraction types
    attraction_expanded = destinations['AttractionType'].str.split(',', expand=True).stack().reset_index(level=1,
                                                                                                         drop=True)
    attraction_expanded.name = 'AttractionType'
    attractions = destinations.drop(columns=['AttractionType']).join(attraction_expanded)
    attractions.dropna(inplace=True)

    # get recommended attractions
    mask = attractions["AttractionType"].isin(group_profile)
    matched_attractions = attractions[mask]

    # get unique attraction ids
    matched_attractions_named = matched_attractions['AttractionId'].unique()
    matched_attractions_mask = destinations['AttractionId'].isin(matched_attractions_named)
    matched_attractions_formatted = destinations[matched_attractions_mask]

    return matched_attractions_formatted


def rank_recommended_attractions(suitable_destinations: pd.DataFrame, group_profile: List) -> pd.DataFrame:
    # Expand AttractionTypeId to multiple rows
    attractionTypeId_expanded = suitable_destinations['AttractionType'].str.split(',', expand=True).stack().reset_index(
        level=1, drop=True)
    attractionTypeId_expanded.name = 'AttractionType_expanded'

    # Merge expanded attraction types with original data
    recommended_attractions_expanded = suitable_destinations.drop(columns=['AttractionType']).join(
        attractionTypeId_expanded)

    # Count how many AttractionTypeIds match the group profile
    recommended_attractions_expanded['match'] = recommended_attractions_expanded['AttractionType_expanded'].isin(
        group_profile).astype(int)

    # Aggregate matches per attraction
    attraction_rank = recommended_attractions_expanded.groupby(['AttractionId', 'Attraction'])[
        'match'].sum().reset_index()

    # Sort by match count in descending order
    ranked_attractions = attraction_rank.sort_values(by='match', ascending=False)

    return ranked_attractions


def get_recommendations(travel_group, destinations):
    final_encoded_preferences = one_hot_encode_preferences(travel_group)
    group_profile = extract_group_profile(final_encoded_preferences)
    group_profile_lst = list(
        item for itemset in group_profile["itemsets"] for item in itemset
    )

    suitable_destinations = get_suitable_destinations(destinations, group_profile_lst)
    ranked_attractions = rank_recommended_attractions(suitable_destinations, group_profile_lst)

    return ranked_attractions.head(6)


####################### After Votes #######################

def get_votes(trip_id: int) -> pd.DataFrame:
    """
    Member	000369	000481	000640	000650	000673	000737	000748	000749	000824	000841
0	52754	7	4	8	5	7	10	3	7	8	5
1	26150	4	8	8	3	6	5	2	8	6	2
2	73724	5	1	10	6	9	1	10	3	7	4

    :param trip_id:
    :return:
    """
    pass


def get_binary_matrix_from_vote(voting_results: pd.DataFrame) -> pd.DataFrame:
    binary_voting_results = voting_results
    binary_voting_results.iloc[:, 1:] = (binary_voting_results.iloc[:, 1:] >= 5).astype(int)
    return binary_voting_results


def find_frequent_poi_itemsets(binary_voting_results, travel_group: pd.DataFrame) -> pd.DataFrame:
    for_apriori_df = binary_voting_results.drop(columns=["Member"])
    members = list(travel_group["UserId"].unique())

    if len(members) > 1:
        min_support = 2 / len(members)  # Minimum support threshold
        frequent_itemsets = apriori(for_apriori_df, min_support=min_support, use_colnames=True)
        frequent_itemsets = frequent_itemsets[
            frequent_itemsets["itemsets"].apply(len) == 1
            ]
    else:
        voted_dest = for_apriori_df.columns[for_apriori_df.iloc[0] == 1].tolist()
        data = {'support': [1.0] * len(voted_dest), 'itemsets': [{dest} for dest in voted_dest]}
        frequent_itemsets = pd.DataFrame(data)

    return frequent_itemsets


def get_best_destinations(trip_id: int, travel_group: pd.DataFrame, destinations: pd.DataFrame) -> pd.DataFrame:
    voting_results = get_votes(trip_id)
    binary_voting_results = get_binary_matrix_from_vote(voting_results)
    frequent_itemsets = find_frequent_poi_itemsets(binary_voting_results, travel_group)

    recommended_dests = frequent_itemsets.sort_values(by="support", ascending=False)
    recommended_dests = recommended_dests[recommended_dests['support'] >= 0.5]
    top_dest = recommended_dests.head(1)

    all_recommended_dests = [item for subset in top_dest['itemsets'] for item in subset]
    unique_recommended_dests = list(pd.unique(all_recommended_dests))

    voted_suitable_dests_mask = destinations['AttractionId'].isin(unique_recommended_dests)
    voted_suitable_dests = destinations[voted_suitable_dests_mask]

    return voted_suitable_dests
