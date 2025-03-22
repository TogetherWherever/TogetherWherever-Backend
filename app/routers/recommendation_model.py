import json
import os
from typing import List

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import HTTPException
from mlxtend.frequent_patterns import apriori
from sqlalchemy.orm import Session

from app.models import Trips, User

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


def get_nearby_destinations_from_api(lat: float, lon: float) -> pd.DataFrame:
    """
        Get nearby places from Google Places API (Nearby Search).
        :param lat: Latitude
        :param lon: Longitude
        :return: List of nearby places
        """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = json.dumps({
        # Exclude certain place types to avoid irrelevant results
        "excludedTypes": ["car_dealer", "car_rental", "car_repair", "car_wash", "electric_vehicle_charging_station",
                          "gas_station", "parking", "rest_stop", "city_hall", "courthouse", "embassy", "fire_station",
                          "government_office", "local_government_office", "police", "post_office", "chiropractor",
                          "dental_clinic", "dentist", "doctor", "drugstore", "hospital", "pharmacy", "physiotherapist",
                          "medical_lab", "apartment_building", "apartment_complex", "condominium_complex",
                          "housing_complex", "bed_and_breakfast", "hotel", "corporate_office", "lodging", "accounting",
                          "atm", "bank", "funeral_home", "insurance_agency", "lawyer", "real_estate_agency", "storage",
                          "telecommunications_service_provider", "department_store", "electronics_store",
                          "grocery_store", "hardware_store", "supermarket", "warehouse_store", "airport",
                          "train_station"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": 8000  # Set radius to 8 km
            }
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.types'  # Optimized field mask
    }

    res = requests.request("POST", url, headers=headers, data=payload)
    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")

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
    attraction_expanded = destinations['AttractionType'].str.split(',', expand=True).stack().reset_index(level=1, drop=True)
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


def get_recommendations(travel_group, destinations):
    final_encoded_preferences = one_hot_encode_preferences(travel_group)
    group_profile = extract_group_profile(final_encoded_preferences)
    group_profile_lst = list(
        item for itemset in group_profile["itemsets"] for item in itemset
    )

    suitable_destinations = get_suitable_destinations(destinations, group_profile_lst)

    return suitable_destinations


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
