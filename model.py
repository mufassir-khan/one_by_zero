import time
from data import Data

from functools import partial

from manager import get_manager_and_routing_model
from solution_reader import get_output_txt
from solver import get_solution


def main(
    data_class: Data,
    one_driver_one_order_bool: bool = True,
    outfile_file_path: str = "output.txt",
):
    manager, routing = get_manager_and_routing_model(data_class)

    print("Routing model created successfully!")

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        # Calculate distance between nodes
        distance = data_class.distance_matrix[from_node][to_node]

        return distance

    def cost_callback(from_index, to_index, cost_per_meter):
        distance = distance_callback(from_index, to_index)
        cost = distance * cost_per_meter

        return cost

    def travel_time_callback(from_index, to_index, speed_in_mps):
        distance = distance_callback(from_index, to_index)
        time = distance / speed_in_mps

        return int(round(time, 0))

    bike_transit_cost_callback = partial(
        cost_callback, cost_per_meter=data_class.cost_per_meter_dict["BIKE"]
    )
    car_transit_cost_callback = partial(
        cost_callback, cost_per_meter=data_class.cost_per_meter_dict["CAR"]
    )

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)

    bike_transit_cost_callback_index = routing.RegisterTransitCallback(
        bike_transit_cost_callback
    )
    car_transit_cost_callback_index = routing.RegisterTransitCallback(
        car_transit_cost_callback
    )

    # Define cost of each arc.
    for _, row in data_class.driver_df.iterrows():
        v_id = row["driver_id"]
        v_type = row["vehicle"]
        if v_type == "BIKE":
            routing.SetArcCostEvaluatorOfVehicle(bike_transit_cost_callback_index, v_id)
        elif v_type == "CAR":
            routing.SetArcCostEvaluatorOfVehicle(car_transit_cost_callback_index, v_id)

    print("Cost of each arc defined successfully!")

    # Add Distance dimension to track distances
    dimension_name = "Distance"
    routing.AddDimension(
        distance_callback_index,
        0,  # no slack
        int(sum(data_class.distance_matrix[1]))
        * 1000,  # vehicle maximum travel distance to be large
        True,  # start cumul to zero
        dimension_name,
    )
    distance_dimension = routing.GetDimensionOrDie(dimension_name)

    # Apply constraints

    # [START pickup_delivery_constraint]
    for request in data_class.pickups_deliveries:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
        )
        routing.solver().Add(
            distance_dimension.CumulVar(pickup_index)
            <= distance_dimension.CumulVar(delivery_index)
        )
    # [END pickup_delivery_constraint]
    print("Pickup & Delivery constraints applied successfully!")

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data_class.demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data_class.vehicle_capacities,  # vehicle maximum capacities
        True,  # start cumul to zero
        "Capacity",
    )
    print("Capacity constraints applied successfully!")

    # Add single driver single order constraint.
    if one_driver_one_order_bool:

        def order_count_callback(from_index):
            """Returns the demand of the node."""
            # Convert from routing variable Index to demands NodeIndex.
            from_node = manager.IndexToNode(from_index)
            return data_class.order_counts[from_node]

        order_count_callback_index = routing.RegisterUnaryTransitCallback(
            order_count_callback
        )

        routing.AddDimension(
            order_count_callback_index,
            0,  # null order count slack
            1,  # vehicle maximum order count is 1
            True,  # start cumul to zero
            "OrderCount",
        )
        print("Single Driver Single Order constraints applied successfully!")

    bike_travel_time_callback = partial(
        travel_time_callback, speed_in_mps=data_class.speed_mps_dict["BIKE"]
    )
    car_travel_time_callback = partial(
        travel_time_callback, speed_in_mps=data_class.speed_mps_dict["CAR"]
    )

    bike_travel_time_callback_index = routing.RegisterTransitCallback(
        bike_travel_time_callback
    )
    car_travel_time_callback_index = routing.RegisterTransitCallback(
        car_travel_time_callback
    )

    travel_time_callback_indices = (
        data_class.driver_df["vehicle"]
        .apply(
            lambda x: bike_travel_time_callback_index
            if x == "BIKE"
            else car_travel_time_callback_index
        )
        .to_list()
    )
    dimension_name = "Time"
    routing.AddDimensionWithVehicleTransitAndCapacity(
        travel_time_callback_indices,
        data_class.max_time_for_any_vehicle,  # Max Slack
        [data_class.max_time_for_any_vehicle]
        * data_class.driver_df.shape[0],  # vehicle maximum travel time
        False,  # don't start cumul to zero
        dimension_name,
    )

    time_dimension = routing.GetDimensionOrDie(dimension_name)

    for location_idx, time_window in enumerate(data_class.time_windows):
        if location_idx in data_class.veh_start_indices + data_class.veh_end_indices:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetMin(time_window[0])
        time_dimension.SetCumulVarSoftUpperBound(
            index, time_window[1], data_class.tw_violation_penalty
        )

    for _, row in data_class.driver_df.iterrows():
        vehicle_id = row["driver_id"]
        tw_min = row["shift_start_sec"]
        tw_max = row["shift_end_sec"]

        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(tw_min, tw_max)

    # Instantiate route start and end times to produce feasible times.
    # [START depot_start_end_times]
    for i in range(data_class.num_vehicles):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i))
        )
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))
    # [END depot_start_end_times]
    print("Soft Time Window constraints applied successfully!")

    # Get solution
    start_time = time.time()
    solution = get_solution(routing)
    time_taken = time.time() - start_time
    print(f"Solution found in {int(time_taken)} seconds !!")

    output_txt = get_output_txt(manager, routing, solution, data_class)

    # Write the string to the file
    with open(outfile_file_path, "w") as file:
        file.write(output_txt)

    return manager, routing, solution, output_txt
