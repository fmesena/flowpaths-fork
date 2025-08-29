import flowpaths as fp
import os
from datetime import datetime

SOLVER = "gurobi"   # "highs"
TIME_LIMIT   = 30
EDGE_FILTER  = 25
current_time = datetime.now()
dt_day       = current_time.strftime("%d-%m")
dt_time      = current_time.strftime("%H-%M")
test_dir     = "../../create-flow-graphs/"
dataset     = "graphs-g5-w5000-k27-cyc"       #EXACT MFD 
dataset_075 = "graphs-g5-w5000-k27-cyc-e0.75" #ABS-ERRORS AND MINPATH-ERROR


def test_min_flow_decomp(filename: str):
    graph = fp.graphutils.read_graphs(filename)[0]

    out = open(dataset + "_" + SOLVER + "_{}_{}.txt".format(dt_day, dt_time), "a")
    out.write(f"#Graph {graph.graph['id']}\n")
    out.write(f"{graph.graph['n']},{graph.graph['m']},{graph.graph['w']}\n")

    #Vanilla
    mfd_model = fp.MinFlowDecompCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": False, # set to false to deactivate the safe sequences optimization
        },
        solver_options={
            "external_solver": SOLVER,
            "time_limit": TIME_LIMIT,
        },
    )
    mfd_model.solve()
    if mfd_model.is_solved():
        assert(mfd_model.is_valid_solution()) # Keep this to verify the solution
    out.write(f"solved_default: {mfd_model.is_solved()}\n")
    out.write(f"time_default:   {mfd_model.solve_statistics['solve_time'] if mfd_model.is_solved() else 0}\n")

    #SAFETY
    mfd_model = fp.MinFlowDecompCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": True, # set to false to deactivate the safe sequences optimization
        },
        solver_options={
            "external_solver": "gurobi", # we can try also "highs" at some point
            "time_limit": TIME_LIMIT,
        },
    )
    mfd_model.solve()
    write_stats_to_file(mfd_model, out)

    out.close()


def test_least_abs_errors(filename):
    graph = fp.graphutils.read_graphs(filename)[0]
    print("graph id", graph.graph["id"])

    out = open(dataset_075 + "_" + SOLVER + "_abs_{}_{}.txt".format(dt_day, dt_time), "a")
    out.write(f"#Graph {graph.graph['id']}\n")
    out.write(f"{graph.graph['n']},{graph.graph['m']},{graph.graph['w']}\n")

    # note that here below we are not passing k, as it will be chosen as the graph width
    klae_model = fp.kLeastAbsErrorsCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": False, # set to false to deactivate the safe sequences optimization
        },
        solver_options={
            "external_solver": SOLVER, # we can try also "highs" at some point
            "time_limit": TIME_LIMIT,
        },
    )

    klae_model.solve()
    if klae_model.is_solved():
        assert(klae_model.is_valid_solution()) # Keep this to verify the solution
    out.write(f"solved_default: {klae_model.is_solved()}\n")
    out.write(f"time_default:   {klae_model.solve_statistics['solve_time'] if klae_model.is_solved() else 0}\n")

    # here we also pass the percentile
    klae_percentile_model = fp.kLeastAbsErrorsCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": True, # set to false to deactivate the safe sequences optimization
        },
        solver_options={
            "external_solver": SOLVER, 
            "time_limit": TIME_LIMIT,
        },
        trusted_edges_for_safety_percentile=EDGE_FILTER, # we trust for safety edges whose weight in >= EDGE_FILTER percentile, remove this if not using the safety optimization
    )
    klae_percentile_model.solve()
    write_stats_to_file(klae_percentile_model, out)


def test_min_path_error(filename):
    graph = fp.graphutils.read_graphs(filename)[0]
    print("graph id", graph.graph["id"])

    out = open(dataset_075 + "_" + SOLVER + "_min_{}_{}.txt".format(dt_day, dt_time), "a")
    out.write(f"#Graph {graph.graph['id']}\n")
    out.write(f"{graph.graph['n']},{graph.graph['m']},{graph.graph['w']}\n")

    kmpe_model = fp.kMinPathErrorCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": False, # set to false to deactivate the safe sequences optimization
        },
        solver_options={
            "external_solver": SOLVER, # we can try also "highs" at some point
            "time_limit": TIME_LIMIT, # 300s = 5min, is it ok?
        },
    )

    kmpe_model.solve()
    if kmpe_model.is_solved():
        assert(kmpe_model.is_valid_solution()) # Keep this to verify the solution
    out.write(f"solved_default: {kmpe_model.is_solved()}\n")
    out.write(f"time_default:   {kmpe_model.solve_statistics['solve_time'] if kmpe_model.is_solved() else 0}\n")


    # we use percentile also here, which overrides the default behavior of trusting all edges
    kmpe_percentile_model = fp.kMinPathErrorCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": True, # set to false to deactivate the safe sequences optimization
        },
        solver_options={
            "external_solver": SOLVER,
            "time_limit": TIME_LIMIT,
        },
        trusted_edges_for_safety_percentile=EDGE_FILTER, # remove this if not using the safety optimization
    )
    kmpe_percentile_model.solve()
    write_stats_to_file(kmpe_percentile_model, out)


def write_stats_to_file(model, file):
    if model.is_solved():
        assert(model.is_valid_solution()) # Keep this to verify the solution
        statistics = model.solve_statistics
        file.write(f"edge_variables=1:          {statistics['edge_variables=1']}\n")
        file.write(f"edge_variables>=1:         {statistics['edge_variables>=1']}\n")
        file.write(f"preprocess_safety:         {statistics.get('safe_sequences_time', 0)}\n")
        file.write(f"number_of_nontrivial_SCCs: {statistics['number_of_nontrivial_SCCs']}\n")
        file.write(f"size_of_largest_SCC:       {statistics['size_of_largest_SCC']}\n")
    file.write(f"solved_safety:                 {model.is_solved()}\n")
    file.write(f"time_safety:                   {statistics['solve_time'] if model.is_solved() else 0}\n")
    return


def main():

    for entry in os.listdir(test_dir+dataset):
        
        if entry.endswith(".graph"):
            file = os.path.join(test_dir+dataset, entry)

            test_min_flow_decomp(filename = file)

    for entry in os.listdir(test_dir+dataset_075):
        
        if entry.endswith(".graph"):
            file = os.path.join(test_dir+dataset_075, entry)
            
            test_least_abs_errors(filename = file)
            test_min_path_error(filename = file)


if __name__ == "__main__":
    # Configure logging
    fp.utils.configure_logging(
        level=fp.utils.logging.INFO,
        log_to_console=True,
    )
    main()
