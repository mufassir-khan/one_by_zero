from dataclasses import dataclass
import os
import pickle
from geopy.distance import geodesic
import pandas as pd


@dataclass
class Dist_Mat:
    order_df: pd.DataFrame
    driver_df: pd.DataFrame
    dummy_depot_count: int = 1
    pickling: bool = True
    dm_pickle_file_path: str = "dm.pkl"

    def __post_init__(self):
        self.get_coordinates()
        self.initiate_dist_mat()
        self.create_distance_matrix()

    @staticmethod
    def calculate_distance(coord1, coord2):
        return int(geodesic(coord1, coord2).meters)

    def get_coordinates(self):
        self.pickup_coordinates = self.order_df[
            ["restaurant_lat", "restaurant_long"]
        ].values.tolist()
        self.drop_coordinates = self.order_df[
            ["customer_lat", "customer_long"]
        ].values.tolist()
        self.veh_start_coordinates = self.driver_df[
            ["start_location_lat", "start_location_long"]
        ].values.tolist()

        self.cust_coordinates = self.pickup_coordinates + self.drop_coordinates

        self.all_coordinates = self.cust_coordinates + self.veh_start_coordinates
        self.all_coordinates_count = len(self.all_coordinates)

    def initiate_dist_mat(self):
        self.distance_matrix = [
            [0] * (self.all_coordinates_count + self.dummy_depot_count)
            for _ in range(self.all_coordinates_count + self.dummy_depot_count)
        ]

        assert (
            len(self.distance_matrix)
            == self.all_coordinates_count + self.dummy_depot_count
        ), "Shape of initial distance matrix is not consistent!!"

    def calculate_dist_mat(self):
        for i in range(self.all_coordinates_count):
            for j in range(self.all_coordinates_count):
                self.distance_matrix[i + self.dummy_depot_count][
                    j + self.dummy_depot_count
                ] = self.calculate_distance(
                    self.all_coordinates[i], self.all_coordinates[j]
                )

        with open(self.dm_pickle_file_path, "wb") as fp:  # Pickling
            pickle.dump(self.distance_matrix, fp)

    def create_distance_matrix(self):
        if self.pickling:
            if os.path.exists(self.dm_pickle_file_path):
                with open(self.dm_pickle_file_path, "rb") as fp:  # Unpickling
                    self.distance_matrix = pickle.load(fp)
            else:
                self.calculate_dist_mat()
        else:
            self.calculate_dist_mat()
