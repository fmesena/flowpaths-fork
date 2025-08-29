import flowpaths as fp
from collections import defaultdict
import re

TIME_LIMIT = 3
data  = "graphs-g5-w5000-k27-cyc_out.txt"
data2 = "graphs-g5-w5000-k27-cyc-e0.75_out.txt"

width_ranges = {
    "1-3": (1, 3),
    "4-6": (4, 6),
    "7-9": (7, 9),
    "10-15": (10, 15),
    "16+": (16, 10000)
}


def parse_input_file(filename):
    data = defaultdict(list)
    current_graph = None

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()

            if line.startswith('#Graph'):
                current_graph = int(line.split()[1])

            elif current_graph is not None:
                if re.match(r'\d+,\s*\d+,\s*\d+', line): #pattern matching on 3 integers separated by commas with arbitrarily many spaces in between
                    n, m, w = map(int, line.split(','))

                    data[current_graph] = {
                        'n': n, 'm': m, 'w': w,
                        'solved_default': None, 'time_default': None,
                        'solved_safety': None, 'time_safety': None,
                        'preprocess_safety': None,
                        'edge_variables=1': None, 'edge_variables>=1': None,
                        'size_of_largest_SCC': None, 'number_of_nontrivial_SCCs': None
                    }
                
                elif 'solved' in line or 'time' in line or 'preprocess' in line or 'variable' in line or 'SCC' in line:

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


def group_by_width(parsed_data):

    width_ranges = {
        "1-3": (1, 3),
        "4-6": (4, 6),
        "7-9": (7, 9),
        "10-15": (10,15),
        "16+": (16, 10000)
    }
    
    grouped_data = {key: {
        'graphs': 0, 'vertices' : [], 'edges': [],
        'preprocess_safety': [],
        'fixedvars_to_one': [], 'fixedvars_to_atleast_one': [],
        'solved_default': 0, 'solved_safety': 0,
        'time_default': [], 'time_safety': [],
        'number_of_nontrivial_SCCs': [], 'size_of_largest_SCC': [],
        'speedup': [],
        'solved_in_every_setting': 0,
    } for key in width_ranges}

    for graph, info in parsed_data.items():
        n,m,w = info['n'], info['m'], info['w']
        for range_label, (low, high) in width_ranges.items():
            if low <= w <= high:
                group = grouped_data[range_label]
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
                    group['number_of_nontrivial_SCCs'] .append(info['number_of_nontrivial_SCCs'])
                    group['size_of_largest_SCC']       .append(info['size_of_largest_SCC'])

                if info['solved_default'] and info['solved_safety']:
                    assert(info['time_default'] > 0 and info['time_safety'] > 0)
                    group['speedup'].append(info['time_default'] / info['time_safety'])
                if not info['solved_default'] and info['solved_safety']:
                    assert(info['time_safety'] > 0)
                    group['speedup'].append(TIME_LIMIT / info['time_safety'])
                if info['solved_default'] and not info['solved_safety']:
                    assert(info['time_default'] > 0)
                    print("ahah!",graph.graph["id"])
                    group['speedup'].append(info['time_default'] / (TIME_LIMIT + info['time_default']))

    return grouped_data


def compute_metrics(grouped_data):
    results = {}
    for width_range, group in grouped_data.items():

        results[width_range] = {
            'graphs': group['graphs'],
            'max_width': -1,
            'avg_nodes': -1,
            'max_nodes': -1,
            'avg_edges':  -1,
            'max_edges': -1,
            'preprocess_safety': -1,
            'solved_default': -1,
            'solved_safety': -1,
            'avg_time_default' : -1,
            'avg_time_safety' : -1,
            'fixed_seqs_=1': -1,
            'fixed_seqs_>=1': -1,
            'avg_SCCs': -1,
            'largest_SCC': -1,
            'speedup': -1
        }

        results[width_range]['solved_default'] = group['solved_default']
        results[width_range]['solved_safety']  = group['solved_safety']

        # Averages and max of the number of vertices and edges 
        if group['graphs'] > 0:
            results[width_range]['avg_nodes']   = sum(group['vertices'])/group['graphs']
            results[width_range]['avg_edges']   = sum(group['edges'])/group['graphs']
            results[width_range]['max_nodes']   = max(group['vertices'])
            results[width_range]['max_edges']   = max(group['edges'])
            results[width_range]['avg_SCCs']    = sum(group['number_of_nontrivial_SCCs']) / group['graphs']
            results[width_range]['size_of_largest_SCC'] = max(group['size_of_largest_SCC'])

        # Average safety preprocessing time
        if len(group['preprocess_safety']) > 0:
            assert(len(group['preprocess_safety']) == group['graphs'])
            results[width_range]['preprocess_safety'] = (sum(group['preprocess_safety']) / len(group['preprocess_safety']))

        # Average running times in every setting
        if group['solved_default'] > 0:
            results[width_range]['avg_time_default'] = sum(group['time_default']) / group['solved_default']
        if group['solved_safety'] > 0:
            results[width_range]['avg_time_safety']  = sum(group['time_safety']) / group['solved_safety']

        # Average of fixed vars on solved instances
        if group['solved_safety'] > 0:
            results[width_range]['fixed_seqs_=1']  = 100 * sum(group['fixed_seqs_=1'])  / group['solved_safety']
            results[width_range]['fixed_seqs_>=1'] = 100 * sum(group['fixed_seqs_>=1']) / group['solved_safety']

        # Calculate speedups
        if len(group['speedup']) > 0:
            results[width_range]['speedup'] = sum(group['speedup']) / len(group['speedup'])

    return results


def generate_table(results):
    latex_code = r'''\begin{table}[]
                    \caption{A table. vars shows the percentage of edge variables set to 1 or more.}
                    \begin{center}
                    \begin{tabular}{|r|r|r|r|r|r|r|r|r|r|r|}
                    \hline
                    & \multirow{2}{*}{$w$} 
                    & \multirow{2}{*}{\#g} 
                    & \multirow{2}{*}{\shortstack{avg $n$\\(max $n$)}} 
                    & \multirow{2}{*}{\shortstack{avg $m$\\(max $m$)}}
                    & \multirow{2}{*}{\shortstack{avg SCC size\\(max size)}}
                    & \multirow{2}{*}{prep (s)} 
                    & \multirow{2}{*}{\shortstack{vars \\ (\%)}} 
                    & \multicolumn{2}{c|}{\#solved (avg time (s))} 
                    & \multirow{2}{*}{$\times$} \\ \cline{9-10}
                    
                    & & & & & & & & no safety & safety & \\ \hline
                    
                    \multirow{3}{*}{\rotatebox{90}{\shortstack{\textbf{Dataset}\\\textbf{name}}}}'''

    for width_range, metrics in results.items():
        preprocess_seqs         = f"{metrics['preprocess_seqs']:.3f}" if metrics['preprocess_seqs'] != -1 else "-"
        
        solved_default_time     = (f"{metrics['solved_default']}" if metrics['solved_default'] != -1 else "-") + " (" + (f"{metrics['avg_time_default']:.3f}" if metrics['avg_time_default'] != -1 else "-")  + ")"
        solved_sequences_time    = (f"{metrics['solved_safety']}"  if metrics['solved_safety'] != -1 else "-")  + " (" + (f"{metrics['avg_time_safety']:.3f}"  if metrics['avg_time_safety']  != -1 else "-")  + ")"

        fixed_sequences_to_1    = f"{metrics['fixed_seqs_=1']:.1f}" if metrics['fixed_seqs_=1'] != -1 else "-"
        fixed_sequences_atleast = f"{metrics['fixed_seqs_>=1']:.1f}" if metrics['fixed_seqs_>=1'] != -1 else "-"

        speedup                 = f"{metrics['speedup']:.1f}" if metrics['speedup'] != -1 else "-"

        nodes_info              = ((f"{int(metrics['nodes'])}") + " (" + f"{metrics['max_nodes']}" + ")" ) if metrics['nodes'] != -1 else "-"
        edges_info              = ((f"{int(metrics['edges'])}") + " (" + f"{metrics['max_edges']}" + ")" ) if metrics['edges'] != -1 else "-"

        SCC_info                = ((f"{int(metrics['avg_SCCs'])}") + " (" + f"{metrics['max_SCCs']}" + ")" ) if metrics['avg_SCCs'] != -1 else "-"

        latex_code += f"& {width_range} & {metrics['graphs']} & {nodes_info} & {edges_info} & {preprocess_seqs} & {SCC_info} & {fixed_sequences_atleast} & {solved_default_time} & {solved_sequences_time} & {speedup} \\\\\n"

    #& & & & & & & & & & \\ \hline
    latex_code += r'''
                    \end{tabular}
                    \end{center}
                    \end{table}
                    '''
    return latex_code



def main():

    parsed_data  = parse_input_file(data)
    grouped_data = group_by_width(parsed_data)
    results      = compute_metrics(grouped_data)
    latex_code   = generate_table(results)
    with open(data+".tex", "w") as f:
        f.write(latex_code)

