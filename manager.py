from functools import partial

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from data import Data


def get_manager_and_routing_model(data_class: Data):
    distance_matrix = data_class.distance_matrix

    # Create the Routing Index Manager
    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix),
        data_class.num_vehicles,
        data_class.veh_start_indices,
        data_class.veh_end_indices,
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    return manager, routing
