import flowpaths as fp
import os
from datetime import datetime

TIME_LIMIT   = 3
current_time = datetime.now()
dt_day       = current_time.strftime("%d-%m")
dt_time      = current_time.strftime("%H-%M")
test_dir     = "../../create-flow-graphs/"


def test_min_flow_decomp(filename: str):
    graph = fp.graphutils.read_graphs(filename)[0]
    print("graph id", graph.graph["id"])
    # print("subset_constraints", graph.graph["constraints"])

    out = open(filename + "_out_{}_{}.txt".format(dt_day, dt_time), "a")
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
            "external_solver": "gurobi", # we can try also "highs" at some point
            "time_limit": TIME_LIMIT, # 300s = 5min
        },
    )
    mfd_model.solve()
    statistics = mfd_model.solve_statistics

    if mfd_model.is_solved():
        assert(mfd_model.is_valid_solution()) # Keep this to verify the solution
        solved_by_default = True
    else:
        print("Model could not be solved.")

    out.write(f"solved_default: {solved_by_default}\n")
    out.write(f"time_default: {statistics['solve_time'] if solved_by_default else 0}\n")

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
            "time_limit": TIME_LIMIT, # 300s = 5min
        },
    )
    mfd_model.solve()
    statistics = mfd_model.solve_statistics

    if mfd_model.is_solved():
        assert(mfd_model.is_valid_solution()) # Keep this to verify the solution
        solved_by_safety = True
        out.write(f"edge_variables=1: {statistics['edge_variables=1']}\n")
        out.write(f"edge_variables>=1: {statistics['edge_variables>=1']}\n")
        out.write(f"preprocess_safety: {statistics.get('safe_sequences_time',0)}\n")
        out.write(f"number_of_nontrivial_SCCs: {statistics['number_of_nontrivial_SCCs']}\n")
        out.write(f"size_of_largest_SCC: {statistics['size_of_largest_SCC']}\n")
    else:
        print("Model could not be solved.")

    out.write(f"solved_safety: {solved_by_safety}\n")
    out.write(f"time_safety: {statistics['solve_time'] if solved_by_safety else 0}\n")

    out.close()


#################################


def main():

    dataset     = test_dir + "graphs-g5-w5000-k27-cyc"       #EXACT MFD 
    dataset_075 = test_dir + "graphs-g5-w5000-k27-cyc-e0.75" #ABS-ERRORS AND MINPATH-ERROR

    for entry in os.listdir(dataset):
        
        if entry.endswith(".graph"):
            file = os.path.join(dataset, entry)

            test_min_flow_decomp(filename = file)
            #test_least_abs_errors(filename = dataset_folder_075, stats = stats)
            #test_min_path_error(filename = dataset_folder_075, stats = stats)


if __name__ == "__main__":
    # Configure logging
    fp.utils.configure_logging(
        level=fp.utils.logging.INFO,
        log_to_console=True,
    )
    main()
