import pandas as pd
from fastapi import Depends
from mlxtend.frequent_patterns import apriori

from app.database import get_db
from app.models import Trips, User

db = Depends(get_db)


def get_travel_group_preferences(trip_id: int) -> pd.DataFrame:
    """
    Get the preferences of the travel group.

    :param trip_id: The ID of the trip.
    :return: DataFrame containing UserId and Preferences columns.
    """
    # Get the companion IDs
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()
    companion_ids = trip.companion.split(",") if trip.companion else []
    companion_ids.append(str(trip.user_id))  # Ensure consistency in ID format

    travel_group = [int(companion_id) for companion_id in companion_ids]

    # Get the preferences of the travel group
    travel_group_preferences = db.query(User).filter(User.user_id.in_(travel_group)).all()

    # Convert to DataFrame with correct structure
    travel_group_preferences_df = pd.DataFrame([
        {"UserId": user.user_id, "Preferences": user.preferences}
        for user in travel_group_preferences
    ])

    return travel_group_preferences_df


def one_hot_encode_preferences(travel_group):
    expanded_preferences = (
        travel_group["Preferences"]
        .str.split(",", expand=True)
        .stack()
        .reset_index(level=1, drop=True)
    )
    expanded_preferences.name = "AttractionTypeId"

    unique_attractions = expanded_preferences.unique()
    one_hot = pd.DataFrame(0, index=travel_group.index, columns=unique_attractions)

    for idx, row in travel_group.iterrows():
        preferences = row["Preferences"].split(", ")
        for pref in preferences:
            one_hot.at[idx, pref] = 1

    return one_hot


def extract_group_profile(encoded_travel_group):
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
        result = pd.DataFrame(data)
        return result


def get_suitable_destinations(target_city, group_profile):
    # # get recommended attractions
    # mask = target_city["AttractionTypeId"].isin(group_profile)
    # matched_attractions = target_city[mask]
    # matched_attractions_named = matched_attractions["AttractionId"].unique()
    # matched_attractions_mask = attraction_dataset["AttractionId"].isin(
    #     matched_attractions_named
    # )
    # matched_attractions_formatted = attraction_dataset[matched_attractions_mask]
    #
    # return matched_attractions_formatted
    pass


def get_recommendations(travel_group, target_city):
    final_encoded_preferences = one_hot_encode_preferences(travel_group)
    group_profile = extract_group_profile(final_encoded_preferences)
    group_profile_lst = list(
        item for itemset in group_profile["itemsets"] for item in itemset
    )
    suitable_destinations = get_suitable_destinations(target_city, group_profile_lst)

    return suitable_destinations
