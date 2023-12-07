from dataclasses import dataclass, field
from typing import Dict, List

from input import Input
from distance_matrix import Dist_Mat


@dataclass
class Data:
    order_data_path: str
    driver_data_path: str
    cost_per_meter_dict: Dict[str, int] = field(init=True, default_factory=dict)
    speed_kmph_dict: Dict[str, int] = field(init=True, default_factory=dict)
    capacity_units_dict: Dict[str, int] = field(init=True, default_factory=dict)
    dummy_depot_count: int = 1
    dummy_depot_time_windows: List[List[int]] = field(init=True, default_factory=list)
    tw_violation_penalty: int = 1  # $1/second
    max_time_for_any_vehicle: int = 7200
    pickling: bool = True
    dm_pickle_file_path: str = "dm.pkl"

    def __post_init__(self):
        self.process_inputs()
        self.get_dm()
        self.get_num_vehicles()
        self.get_vehicle_start_indices()
        self.get_vehicle_end_indices()
        self.get_demands()
        self.get_pickup_delivery_pairs()
        self.get_vehicle_capacities()
        self.get_time_windows()

    def process_inputs(self):
        self.input_class = Input(
            order_data_path=self.order_data_path, driver_data_path=self.driver_data_path
        )
        self.order_df = self.input_class.order_df
        self.driver_df = self.input_class.driver_df

        self.check_vehicle_type_input_dicts()

        assert (
            not self.veh_type_not_in_cost_dict
        ), f"Missing costs for {self.veh_type_not_in_cost_dict} vehicle types !!"
        assert (
            not self.veh_type_not_in_speed_dict
        ), f"Missing speed for {self.veh_type_not_in_speed_dict} vehicle types !!"
        assert (
            not self.veh_type_not_in_capacity_dict
        ), f"Missing capacities for {self.veh_type_not_in_capacity_dict} vehicle types !!"

        self.driver_df["cost_per_meter"] = self.driver_df["vehicle"].map(
            self.cost_per_meter_dict
        )

        self.speed_mps_dict = {
            k: v * 1000 / 3600 for k, v in self.speed_kmph_dict.items()
        }
        self.driver_df["speed_meter_per_sec"] = self.driver_df["vehicle"].map(
            self.speed_mps_dict
        )

        self.driver_df["capacity"] = self.driver_df["vehicle"].map(
            self.capacity_units_dict
        )

    def get_dm(self):
        self.dm_class = Dist_Mat(
            order_df=self.order_df,
            driver_df=self.driver_df,
            dummy_depot_count=self.dummy_depot_count,
            pickling=self.pickling,
            dm_pickle_file_path=self.dm_pickle_file_path,
        )
        self.distance_matrix = self.dm_class.distance_matrix

    def get_num_vehicles(self):
        self.num_vehicles = self.driver_df.shape[0]

    def get_vehicle_start_indices(self):
        self.veh_start_indices = [
            len(self.dm_class.cust_coordinates) + i + self.dummy_depot_count
            for i in range(self.driver_df.shape[0])
        ]

    def get_vehicle_end_indices(self):
        self.veh_end_indices = [0 for _ in range(self.driver_df.shape[0])]

    def get_demands(self):
        dummy_pickups_drop_demands = (
            [0]
            + self.order_df["no_of_items"].values.tolist()
            + list(-1 * self.order_df["no_of_items"].values)
        )
        veh_start_node_demands = [
            0
            for _ in range(
                (self.dm_class.all_coordinates_count + self.dummy_depot_count)
                - len(dummy_pickups_drop_demands)
            )
        ]

        self.demands = dummy_pickups_drop_demands + veh_start_node_demands

    def get_vehicle_capacities(self):
        self.vehicle_capacities = self.driver_df["capacity"].values.tolist()

    def get_pickup_delivery_pairs(self):
        self.pickups_deliveries = [
            [i, i + self.order_df.shape[0]]
            for i in range(
                self.dummy_depot_count, self.order_df.shape[0] + self.dummy_depot_count
            )
        ]

    def get_time_windows(self):
        pickup_drop_tw = (
            self.order_df[["prep_duration_sec", "preferred_otd_sec"]].values.tolist()
            * 2
        )
        dummy_pickup_drop_tw = self.dummy_depot_time_windows + pickup_drop_tw
        veh_start_node_tw = self.driver_df[
            ["shift_start_sec", "shift_end_sec"]
        ].values.tolist()

        self.time_windows = dummy_pickup_drop_tw + veh_start_node_tw

    def check_vehicle_type_input_dicts(self):
        self.veh_type_not_in_cost_dict = [
            v
            for v in self.driver_df["vehicle"].unique()
            if v not in self.cost_per_meter_dict.keys()
        ]

        self.veh_type_not_in_speed_dict = [
            v
            for v in self.driver_df["vehicle"].unique()
            if v not in self.speed_kmph_dict.keys()
        ]

        self.veh_type_not_in_capacity_dict = [
            v
            for v in self.driver_df["vehicle"].unique()
            if v not in self.capacity_units_dict.keys()
        ]
