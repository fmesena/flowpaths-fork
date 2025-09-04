from collections import defaultdict
import re
import argparse


def parse_input_file(filename: str) -> dict:
    data = defaultdict(list)
    current_graph = None

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('#Graph'):
                current_graph = str(line.split()[1])

            elif current_graph is not None:
                if re.match(r'\d+,\s*\d+,\s*\d+', line): #pattern matching on 3 integers separated by commas with arbitrarily many spaces in between
                    n, m, w = map(int, line.split(','))

                    data[current_graph] = {
                        'n': n, 'm': m, 'w': w,
                        'solved_default': None, 'time_default': None,
                        'solved_safety': None, 'time_safety': None,
                        'preprocess_safety': None,
                        'edge_variables=1': None, 'edge_variables>=1': None,
                        'size_of_largest_SCC': None, 'number_of_SCCs': None, 'avg_size_of_SCCs': None
                    }
                
                elif 'solved' in line or 'time' in line or 'preprocess' in line or 'edge' in line or 'SCC' in line:

                    key, value = line.split(':')
                    key = key.strip()
                    value = value.strip()

                    if value in ['True', 'False']:
                        value = value == 'True'
                    else:
                        value = float(value)

                    if key in data[current_graph]:
                        data[current_graph][key] = value
    return data


def group_data(parsed_data: dict, tlimit: int) -> dict:

    group = {
        'graphs': 0, 'vertices' : [], 'edges': [], 'widths': [],
        'preprocess_safety': [],
        'edge_variables=1': [], 'edge_variables>=1': [],
        'solved_default': 0, 'solved_safety': 0,
        'time_default': [], 'time_safety': [],
        'number_of_SCCs': [], 'size_of_largest_SCC': [], 'avg_size_of_SCCs': [],
        'speedup': [],
        'solved_in_every_setting': 0,
        }

    for graph, info in parsed_data.items():
        n,m,w = info['n'], info['m'], info['w']

        group['graphs'] += 1
        group['vertices'].append(n)
        group['edges'].append(m)
        group['widths'].append(w)

        if info['solved_default'] and info['solved_safety']:
            group['solved_in_every_setting'] += 1

        if info['solved_default']:
            group['solved_default'] += 1
            group['time_default'].append(info['time_default'])

        if info['solved_safety']:
            group['solved_safety'] += 1
            group['time_safety'].append(info['time_safety'])

            # Account for these statistics only if solved_safety is True
            group['preprocess_safety']         .append(info['preprocess_safety'])
            group['edge_variables=1']          .append(info['edge_variables=1']/(w*m))
            group['edge_variables>=1']         .append(info['edge_variables>=1']/(w*m))
            group['number_of_SCCs']            .append(info['number_of_SCCs'])
            group['size_of_largest_SCC']       .append(info['size_of_largest_SCC'])
            group['avg_size_of_SCCs']          .append(info['avg_size_of_SCCs'])

        if info['solved_default'] and info['solved_safety']:
            assert(info['time_default'] > 0 and info['time_safety'] > 0)
            group['speedup'].append(info['time_default'] / info['time_safety'])
        if not info['solved_default'] and info['solved_safety']:
            assert(info['time_safety'] > 0)
            group['speedup'].append(tlimit / info['time_safety'])
        if info['solved_default'] and not info['solved_safety']:
            assert(info['time_default'] > 0)
            print("ahah!")
            group['speedup'].append(info['time_default'] / (tlimit + info['time_default']))

    return group


def compute_metrics(group):
    results = {
        'graphs': group['graphs'],
        'avg_nodes': -1,
        'max_nodes': -1,
        'avg_edges':  -1,
        'max_edges': -1,
        'avg_width': -1,
        'max_width': -1,
        'preprocess_safety': -1,
        'solved_default': -1,
        'solved_safety': -1,
        'avg_time_default' : -1,
        'avg_time_safety' : -1,
        'edge_variables=1': -1,
        'edge_variables>=1': -1,
        'avg_number_of_SCCs': -1,
        'avg_size_of_largest_SCC': -1,
        'avg_size_of_SCCs': -1,
        'speedup': -1
    }

    results['solved_default'] = group['solved_default']
    results['solved_safety']  = group['solved_safety']

    # Averages and max of the number of vertices and edges 
    if group['graphs'] > 0:
        results['avg_nodes']   = sum(group['vertices'])/group['graphs']
        results['avg_edges']   = sum(group['edges'])/group['graphs']
        results['avg_width']   = sum(group['widths'])/group['graphs']
        results['max_nodes']   = max(group['vertices'])
        results['max_edges']   = max(group['edges'])
        results['max_width']   = max(group['widths'])

    # Average running times in every setting
    if group['solved_default'] > 0:
        results['avg_time_default'] = sum(group['time_default']) / group['solved_default']
    if group['solved_safety'] > 0:
        results['avg_time_safety']   =       sum(group['time_safety'])       / group['solved_safety']
        results['edge_variables=1']  = 100 * sum(group['edge_variables=1'])  / group['solved_safety']
        results['edge_variables>=1'] = 100 * sum(group['edge_variables>=1']) / group['solved_safety']

        #Compute the averages of SCC-related statistics
        results['avg_number_of_SCCs']      = sum(group['number_of_SCCs'])      / group['solved_safety']
        results['avg_size_of_largest_SCC'] = sum(group['size_of_largest_SCC']) / group['solved_safety']
        results['avg_size_of_SCCs']        = max(group['avg_size_of_SCCs'])    / group['solved_safety']
        
        # Average safety preprocessing time
        if len(group['preprocess_safety']) > 0:
            assert(len(group['preprocess_safety']) == group['solved_safety'])
            results['preprocess_safety'] = (sum(group['preprocess_safety']) / len(group['preprocess_safety']))

    # Calculate speedups
    if len(group['speedup']) > 0:
        results['speedup'] = sum(group['speedup']) / len(group['speedup'])

    return results


def generate_table(metrics, entry):

    preprocess_seqs = f"{metrics['preprocess_safety']:.3f}" if metrics['preprocess_safety'] != -1 else "-"
    
    solved_default_time = (
        (f"{metrics['solved_default']}" if metrics['solved_default'] != -1 else "-") +
        " (" +
        (f"{metrics['avg_time_default']:.3f}" if metrics['avg_time_default'] != -1 else "-") +
        ")"
    )
    solved_sequences_time = (
        (f"{metrics['solved_safety']}" if metrics['solved_safety'] != -1 else "-") +
        " (" +
        (f"{metrics['avg_time_safety']:.3f}" if metrics['avg_time_safety'] != -1 else "-") +
        ")"
    )

    fixed_sequences_atleast = f"{metrics['edge_variables>=1']:.1f}" if metrics['edge_variables>=1'] != -1 else "-"

    speedup = f"{metrics['speedup']:.1f}" if metrics['speedup'] != -1 else "-"

    nodes_info = (f"{int(metrics['avg_nodes'])} ({metrics['max_nodes']})"
                    if metrics['avg_nodes'] != -1 else "-")
    edges_info = (f"{int(metrics['avg_edges'])} ({metrics['max_edges']})"
                    if metrics['avg_edges'] != -1 else "-")
    width_info = (f"{int(metrics['avg_width'])} ({metrics['max_width']})"
                    if metrics['avg_width'] != -1 else "-")
    SCC_number = (f"{metrics['avg_number_of_SCCs']:.1f} ({metrics['avg_size_of_largest_SCC']})"
                if metrics['avg_number_of_SCCs'] != -1 else "-")
    SCC_size   = (f"{metrics['avg_size_of_SCCs']:.1f}"
                if metrics['avg_size_of_SCCs'] != -1 else "-")

    return (
        f"  {entry} & {metrics['graphs']} & {nodes_info} & {width_info} & {SCC_number} & {SCC_size} "
        f"& {preprocess_seqs} & {fixed_sequences_atleast} & {solved_default_time} "
        f"& {solved_sequences_time} & {speedup} \\\\ \\hline"
    )
    # genms g   n          m       w          #SCCs         sizeSCCs    prep(s) vars(%) solvedD (avgT) solvedS (avgT) speedup
    # 5  & 47 & 25 (127) & 8 (12) & 1.9 & 98.0   & 0.002 & 8.0  & 47 (0.221) & 47 (0.106) & 1.6 \\ \hline


def main(filenames, tlimit):

    stats_genomes  = ""

    for filename in filenames:

        parsed_data    = parse_input_file(filename)
        grouped_data   = group_data(parsed_data, tlimit)
        results        = compute_metrics(grouped_data)
        latex_code     = generate_table(results, re.search(r"g(\d+)(?=-)", filename).group(1))
        stats_genomes  += latex_code

    print(filenames)
    filename = filenames[0].replace("_", "\\_")

    table_header = f'''
\\begin{{table}}[]
\\caption{{{filename}}}
\\begin{{center}}
\\begin{{tabular}}{{|l|r|r|r|r|r|r|r|r|r|r|}}
\\hline
\\multirow{{2}}{{*}}{{\\#gns}}
& \\multirow{{2}}{{*}}{{\\#g}}
& \\multirow{{2}}{{*}}{{$\\tilde{{m}}$ (max)}}
& \\multirow{{2}}{{*}}{{$\\tilde{{w}}$ (max)}}
& \\multirow{{2}}{{*}}{{\\shortstack{{avg \\# SCCs\\\\(max size)}}}}
& \\multirow{{2}}{{*}}{{\\shortstack{{avg size\\\\of SCCs}}}}
& \\multirow{{2}}{{*}}{{prep (s)}}
& \\multirow{{2}}{{*}}{{vars (\\%)}}
& \\multicolumn{{2}}{{c|}}{{\\#solved (avg time (s))}}
& \\multirow{{2}}{{*}}{{$\\times$}} \\\\ \\cline{{9-10}}

& & & & & & & & no safety & safety & \\\\ \\hline
'''

    latex_tail = '''
\\end{tabular}
\\end{center}
\\end{table}
'''

    with open(filename+".tex", "w") as f:
        f.write(table_header + stats_genomes + latex_tail)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process inputs.')
    parser.add_argument('-i', '--input' , required=True, help='Input file path')
    parser.add_argument('-t', '--tlimit', type=int, default=300, help='Time limit in seconds for the solver')

    args = parser.parse_args()

    main(filename=[args.input], tlimit=args.tlimit)




'''

\begin{table}[]
\caption{JGI-perfect-weights-g5-w50000-k63\_MFD\_gurobi\_300\_03-09\_03-00.txt. vars shows the percentage of edge variables set to 1 or more.}
\begin{center}
\begin{tabular}{|l|r|r|r|r|r|r|r|r|r|r|r|}
\hline
\multirow{2}{*}{\#gns}
& \multirow{2}{*}{\#g}
& \multirow{2}{*}{$\tilde{n}$ (max)}
& \multirow{2}{*}{$\tilde{m}$ (max)}
& \multirow{2}{*}{$\tilde{w}$ (max)}
& \multirow{2}{*}{avg \# SCCs}
& \multirow{2}{*}{\shortstack{avg \# SCCs\\(max size)}} % cloned column
& \multirow{2}{*}{prep (s)}
& \multirow{2}{*}{vars (\%)}
& \multicolumn{2}{c|}{\#solved (avg time (s))}
& \multirow{2}{*}{$\times$} \\ \cline{10-11}

& & & & & & & & & no safety & safety & \\ \hline

5 & 47 & 25 (127) & 25 (127) & 4--6 & 1.9 & 98.0 & 0.002 & 8.0 & 47 (0.221) & 47 (0.106) & 1.6 \\ \hline
10 & 12 & 40 (210) & 60 (350) & 7--9 & 3.2 & 120.5 & 0.010 & 12.5 & 11 (0.540) & 12 (0.310) & 1.7 \\ \hline
15 & 0 & - & - & 10--15 & - & - & - & - & 0 (-) & 0 (-) & - \\ \hline

\end{tabular}
\end{center}
\end{table}


'''