import os
from typing import List

import pandas as pd
from dotenv import load_dotenv
from mlxtend.frequent_patterns import apriori
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Trips, User
from app.routers.discover import get_nearby_places_from_api

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


def get_members(trip_id: int, db: Session) -> List[str]:
    """
    Get the members of the travel group.

    :param trip_id: The ID of the trip.
    :param db: Database session.
    :return: List of usernames of the members.
    """
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()
    members = trip.companion.split(",") if trip.companion else []
    members.append(trip.owner)  # Add the owner to the travel group

    return members


def get_travel_group_preferences(trip_id: int, db: Session) -> pd.DataFrame:
    """
    Get the preferences of the travel group.

    :param db: Database session.
    :param trip_id: The ID of the trip.
    :return: DataFrame containing UserId and Preferences columns.
    """
    # Get the companion IDs
    companions = get_members(trip_id, db)

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


def one_hot_encode_preferences(travel_group: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot encode the preferences of the travel group.

    :param travel_group: The dataframe containing the preferences of the travel group.
    :return: The one-hot encoded preferences.
    """
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
    """
    Extract the group profile from the one-hot encoded preferences.

    :param encoded_travel_group: The one-hot encoded preferences.
    :return: The group profile.
    """
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


async def get_nearby_destinations(lat: float, lon: float, max_result: int = 20, radius: int = 8000) -> pd.DataFrame:
    """
    Get nearby places from Google Places API (Nearby Search).

    :param lat: Latitude
    :param lon: Longitude
    :param max_result: The maximum number of results to return.
    :param radius: The radius in meters to search within.
    :return: List of nearby places
    """
    g_fields = 'places.id,places.displayName,places.types'
    response = await get_nearby_places_from_api(g_fields, lat, lon, max_result, radius)

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
    """
    Get suitable destinations based on the group profile.

    :param destinations: The dataframe containing the destinations details.
    :param group_profile: The group profile.
    :return: The dataframe of suitable destinations.
    """
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
    """
    Rank recommended attractions based on the group profile.

    :param suitable_destinations: The dataframe of suitable destinations.
    :param group_profile: The group profile.
    :return: The ranked attractions.
    """
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


def get_recommendations(travel_group: pd.DataFrame, destinations: pd.DataFrame) -> pd.DataFrame:
    """
    Get recommendations for the travel group.

    :param travel_group: The dataframe containing the preferences of the travel group.
    :param destinations: The dataframe containing the destinations details.
    :return: The ranked recommended attractions.
    """
    final_encoded_preferences = one_hot_encode_preferences(travel_group)
    group_profile = extract_group_profile(final_encoded_preferences)
    group_profile_lst = list(
        item for itemset in group_profile["itemsets"] for item in itemset
    )

    suitable_destinations = get_suitable_destinations(destinations, group_profile_lst)
    ranked_attractions = rank_recommended_attractions(suitable_destinations, group_profile_lst)

    return ranked_attractions.head(6)


####################### After Votes #######################

def get_votes(trip_day_id: int, db: Session) -> pd.DataFrame:
    """
    Retrieve vote scores for a specific trip day and return them as a pivoted DataFrame.

    :param trip_day_id: The ID of the trip day.
    :param db: The database session.
    :return: A Pandas DataFrame with usernames as rows, destination IDs as columns,
             and vote scores as values.
    """
    # Execute the SQL query using SQLAlchemy
    query = text("""
        SELECT vs.username, vs.vote_score, rp.dest_id
        FROM vote_scores vs
        JOIN recommended_places rp ON vs.recommended_place_id = rp.recommended_place_id
        WHERE rp.trip_day_id = :trip_day_id
    """)

    results = db.execute(query, {"trip_day_id": trip_day_id}).fetchall()

    # Convert results into a Pandas DataFrame
    df = pd.DataFrame(results, columns=["username", "vote_score", "dest_id"])

    # Pivot the table: usernames as rows, destination IDs as columns, vote_score as values
    pivot_df = df.pivot(index="username", columns="dest_id", values="vote_score")

    # Reset column names for clarity
    pivot_df = pivot_df.rename_axis(columns=None).reset_index()

    return pivot_df


def get_binary_matrix_from_vote(voting_results: pd.DataFrame) -> pd.DataFrame:
    binary_voting_results = voting_results
    binary_voting_results.iloc[:, 1:] = (binary_voting_results.iloc[:, 1:] >= 5).astype(int)

    return binary_voting_results


def find_frequent_poi_itemsets(binary_voting_results: pd.DataFrame, travel_group: pd.DataFrame) -> pd.DataFrame:
    for_apriori_df = binary_voting_results.drop(columns=["username"])
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


def get_best_destinations(trip_day_id: int, travel_group: pd.DataFrame, destinations: pd.DataFrame, db: Session) -> pd.DataFrame:
    voting_results = get_votes(trip_day_id, db)
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
