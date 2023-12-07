from data import Data


def location_name_from_node(node, data_class: Data):
    classifying_number = len(data_class.distance_matrix) - (
        data_class.dummy_depot_count + data_class.num_vehicles
    )
    if node > classifying_number:
        loc_name = node - (classifying_number) - 1
        name = f"Driver_{loc_name}_Start"

    elif node == 0:
        name = "Route_END"

    else:
        if node > classifying_number / 2:
            loc_name = node - int(classifying_number / 2) - 1
            name = f"order_id_{loc_name}_drop"
        else:
            loc_name = node - 1
            name = f"order_id_{loc_name}_pickup"

    return name


def get_output_txt(manager, routing, solution, data_class: Data):
    txt = ""
    p = f"Objective Cost: ${solution.ObjectiveValue()}\n"
    txt += p
    # print(f"Objective Cost: ${solution.ObjectiveValue()}")

    time_dimension = routing.GetDimensionOrDie("Time")
    distance_dimension = routing.GetDimensionOrDie("Distance")
    total_time = 0
    total_distance = 0
    max_route_cost = 0
    total_route_cost = 0
    total_delay = 0

    p = "########################################################################### \n"
    txt += p
    # print("###########################################################################")
    for vehicle_id in range(data_class.num_vehicles):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for driver {vehicle_id}:\n"
        route_cost = 0
        route_distance = 0
        route_penalty_cost = 0
        route_delay = 0
        p = "======================================================================== \n"
        txt += p
        # print(
        #     "========================================================================"
        # )
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            dist_var = distance_dimension.CumulVar(index)
            location_node = manager.IndexToNode(index)
            n = location_name_from_node(location_node, data_class)
            plan_output += (
                f"{n}"
                f" Time({solution.Min(time_var)},{solution.Max(time_var)})"
                " -> "
            )
            if solution.Min(time_var) >= 2400:
                route_penalty_cost += (solution.Min(time_var) - 2400) * 1
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            # route_distance += solution.Min(dist_var)
            route_cost += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )

        time_var = time_dimension.CumulVar(index)
        dist_var = distance_dimension.CumulVar(index)

        location_node = manager.IndexToNode(index)
        n = location_name_from_node(location_node, data_class)

        plan_output += (
            f"{n}" f" Time({solution.Min(time_var)},{solution.Max(time_var)})\n"
        )

        route_distance = solution.Min(dist_var)
        route_delay += route_penalty_cost
        route_cost += route_penalty_cost * data_class.tw_violation_penalty
        plan_output += f"Time of the route: {solution.Min(time_var)} seconds\n"
        plan_output += f"Cost of the route: ${route_cost}\n"
        plan_output += f"Distance of the route: {solution.Min(dist_var)} meters \n"
        plan_output += f"Delay of the route: {route_delay} seconds\n"

        p = plan_output
        txt += p
        # print(plan_output)
        max_route_cost = max(route_cost, max_route_cost)
        total_route_cost += route_cost
        total_time += solution.Min(time_var)
        total_distance += route_distance
        total_delay += route_delay
    p = "###########################################################################\n"
    txt += p
    # print("###########################################################################")

    p = f"Maximum of the route costs: ${max_route_cost}\n"
    txt += p
    # print(f"Maximum of the route costs: ${max_route_cost}")

    p = f"Total route cost: ${total_route_cost}\n"
    txt += p
    # print(f"Total route cost: ${total_route_cost}")

    p = f"Total route time: {total_time} seconds\n"
    txt += p
    # print(f"Total route time: {total_time} seconds")

    p = f"Total route distance: {total_distance} meters\n"
    txt += p
    # print(f"Total route distance: {total_distance} meters")

    p = f"Total route delay: {total_delay} seconds"
    txt += p
    # print(f"Total route delay: {total_delay} seconds")

    return txt
