from dataclasses import dataclass
import pandas as pd


@dataclass
class Input:
    order_data_path: str
    driver_data_path: str

    def __post_init__(self):
        self.order_df = pd.read_csv(self.order_data_path)
        self.driver_df = pd.read_csv(self.driver_data_path)
        self.data_sanity_check()

    def data_sanity_check(self):
        self.order_df_nan_values_count = self.order_df.isna().sum().sum()
        self.driver_df_nan_values_count = self.driver_df.isna().sum().sum()

        if self.order_df_nan_values_count > 0:
            raise Exception("NAN values found in order data !!")
        if self.driver_df_nan_values_count > 0:
            raise Exception("NAN values found in driver data!!")

        print("Input data sanity check done successfully.")

        # TODO: Column assertions
