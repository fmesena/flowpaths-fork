import flowpaths as fp
import os
from datetime import datetime
import argparse
import stats

test_dir     = "../../flow-datasets/cyclic-graphs/"
current_time = datetime.now()
dt_day       = current_time.strftime("%d-%m")
dt_time      = current_time.strftime("%H-%M")
output_file  = ""
CONFIG = {
    "TIME_LIMIT" : 300,
    "SOLVER"     : "gurobi", #highs
    "EDGE_FILTER": 25
}


def test_min_flow_decomp(input_file: str, output_file: str):
    graph = fp.graphutils.read_graphs(input_file)[0]

    out = open(output_file, "a")
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
            "optimize_with_safe_sequences": False,
        },
        solver_options={
            "external_solver": get_solver(),
            "time_limit": get_timelimit(),
        },
    )
    mfd_model.solve()
    if mfd_model.is_solved():
        assert(mfd_model.is_valid_solution())
    out.write(f"solved_default:            {str(True) if mfd_model.is_solved() else str(False)}\n")
    out.write(f"time_default:              {mfd_model.solve_statistics['solve_time'] if mfd_model.is_solved() else 0}\n")

    #SAFETY
    mfd_model = fp.MinFlowDecompCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": True,
        },
        solver_options={
            "external_solver": get_solver(),
            "time_limit": get_timelimit(),
        },
    )
    mfd_model.solve()
    write_stats_to_file(mfd_model, out)

    out.close()


def test_least_abs_errors(input_file: str, output_file: str):
    graph = fp.graphutils.read_graphs(input_file)[0]

    out = open(output_file, "a")
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
            "optimize_with_safe_sequences": False,
        },
        solver_options={
            "external_solver": get_solver(),
            "time_limit": get_timelimit(),
        },
    )

    klae_model.solve()
    if klae_model.is_solved():
        assert(klae_model.is_valid_solution())
    out.write(f"solved_default:            {str(True) if klae_model.is_solved() else str(False)}\n")
    out.write(f"time_default:              {klae_model.solve_statistics['solve_time'] if klae_model.is_solved() else 0}\n")

    # here we also pass the percentile
    klae_percentile_model = fp.kLeastAbsErrorsCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": True,
        },
        solver_options={
            "external_solver": get_solver(),
            "time_limit": get_timelimit(),
        },
        trusted_edges_for_safety_percentile=get_edgefilter(), # we trust for safety edges whose weight in >= EDGE_FILTER percentile, remove this if not using the safety optimization
    )
    klae_percentile_model.solve()
    write_stats_to_file(klae_percentile_model, out)


def test_min_path_error(input_file: str, output_file: str):
    graph = fp.graphutils.read_graphs(input_file)[0]

    out = open(output_file, "a")
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
            "external_solver": get_solver(),
            "time_limit": get_timelimit(),
        },
    )

    kmpe_model.solve()
    if kmpe_model.is_solved():
        assert(kmpe_model.is_valid_solution())
    out.write(f"solved_default:            {str(True) if kmpe_model.is_solved() else str(False)}\n")
    out.write(f"time_default:              {kmpe_model.solve_statistics['solve_time'] if kmpe_model.is_solved() else 0}\n")


    # we use percentile also here, which overrides the default behavior of trusting all edges
    kmpe_percentile_model = fp.kMinPathErrorCycles(
        G=graph,
        flow_attr="flow",
        weight_type=int,
        #subset_constraints=graph.graph["constraints"], # try with and without
        subset_constraints=[],
        optimization_options={
            "optimize_with_safe_sequences": True,
        },
        solver_options={
            "external_solver": get_solver(),
            "time_limit": get_timelimit(),
        },
        trusted_edges_for_safety_percentile=get_edgefilter(), # remove this if not using the safety optimization
    )
    kmpe_percentile_model.solve()
    write_stats_to_file(kmpe_percentile_model, out)


def write_stats_to_file(model, file):
    solved = model.is_solved()
    file.write(f"solved_safety:             {str(True) if solved else str(False)}\n")

    if solved:
        assert(model.is_valid_solution()) # Keep this to verify the solution
        statistics = model.solve_statistics
        file.write(f"time_safety:               {statistics['solve_time']}\n")
        file.write(f"edge_variables=1:          {statistics['edge_variables=1']}\n")
        file.write(f"edge_variables>=1:         {statistics['edge_variables>=1']}\n")
        file.write(f"preprocess_safety:         {statistics.get('safe_sequences_time', 0)}\n")
        file.write(f"number_of_nontrivial_SCCs: {statistics['number_of_nontrivial_SCCs']}\n")
        file.write(f"size_of_largest_SCC:       {statistics['size_of_largest_SCC']}\n")
    else:
        file.write("time_safety:                0\n")
    
    '''
    if mfd_model.is_solved():
        assert(mfd_model.is_valid_solution())
    out.write(f"solved_default:            {str(True) if mfd_model.is_solved() else str(False)}\n")
    out.write(f"time_default:              {mfd_model.solve_statistics['solve_time'] if mfd_model.is_solved() else 0}\n")

    '''
    
    return


def set_timelimit(x: int):
    CONFIG["TIME_LIMIT"] = x
def get_timelimit():
    return CONFIG["TIME_LIMIT"]
def set_solver(x: str):
    CONFIG["SOLVER"] = x
def get_solver():
    return CONFIG["SOLVER"]
def set_edgefilter(x: int):
    CONFIG["EDGE_FILTER"] = x
def get_edgefilter():
    return CONFIG["EDGE_FILTER"]



def main(mode, dataset, generate_stats):
    ilp_solver = None
    ilp_name = ""

    match mode:
        case '0':
            ilp_solver = test_min_flow_decomp
            ilp_name   = "MFD"
        case '1':
            ilp_solver = test_least_abs_errors
            ilp_name   = "ABS"
        case '2':
            ilp_solver = test_min_path_error
            ilp_name   = "MIN"

    dataset_path = os.path.join(test_dir, dataset)
    for subfolder in os.listdir(dataset_path):
        subfolder_path = os.path.join(dataset_path, subfolder)

        if os.path.isdir(subfolder_path):
            for entry in os.listdir(subfolder_path):
                if entry.endswith(".graph"):
                    file = os.path.join(subfolder_path, entry)
                    rel_path = os.path.relpath(subfolder_path, test_dir) # relative path from test_dir, then turn into filename
                    output_file = (
                        rel_path.replace("/", "-")
                        + "_" + ilp_name
                        + "_" + get_solver()
                        + "_" + str(get_timelimit())
                        + "_{}_{}.txt".format(dt_day, dt_time)
                    )

                    ilp_solver(input_file=file, output_file=output_file)

    if generate_stats:
        stats.main(output_file, get_timelimit())



if __name__ == "__main__":

    # Configure logging
    fp.utils.configure_logging(
        level=fp.utils.logging.INFO,
        log_to_console=True,
    )
    
    parser = argparse.ArgumentParser(description='Process inputs.')

    parser.add_argument('-i', '--input'  , required=True,              help='Input file path')
    parser.add_argument('-m', '--mode'   , required=True,              choices=['0','1','2'] , help='Execution mode') # 0 MFD; 1 ABS; 2 MIN
    parser.add_argument('-s', '--stats'  , action="store_true",        help='Generate statistics automatically')
    parser.add_argument('-t', '--tlimit' , type=int, default=300,      help='Time limit in seconds for the solver')
    parser.add_argument('-e', '--efilter', type=int, default=25,       help='Edge filter value')
    parser.add_argument('-S', '--solver' , type=str, default="gurobi", help='Solver to use: gurobi or highs')

    args = parser.parse_args()

    set_timelimit(args.tlimit)
    set_solver(args.solver)
    set_edgefilter(args.efilter)

    main(mode=args.mode, dataset=args.input, generate_stats=args.stats)
