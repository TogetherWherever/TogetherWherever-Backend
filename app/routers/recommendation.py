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
    travel_group_preferences = (
        db.query(User).filter(User.user_id.in_(travel_group)).all()
    )

    # Convert to DataFrame with correct structure
    travel_group_preferences_df = pd.DataFrame(
        [
            {"UserId": user.user_id, "Preferences": user.preferences}
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
        preferences = row["Preferences"].split(", ")
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


def get_suitable_destinations(destinations: pd.DataFrame, group_profile: pd.DataFrame) -> pd.DataFrame:
    # get recommended attractions
    mask = destinations["AttractionType"].isin(group_profile)
    matched_attractions = destinations[mask]

    return matched_attractions


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
