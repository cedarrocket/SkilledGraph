import json
from skilledgraph import build_graph


def create_graph(path):
    builder = build_graph(path)
    builder.add_edge('Start','SourceA').add_edge('Start','SourceB')
    builder.add_edge(['SourceA','SourceB'],'Report')
    return builder.compile()


def main(graph_path, argv):
    if argv: raise ValueError('This pure-code demo does not accept arguments')
    result = create_graph(graph_path).invoke({'records':{},'events':{},'completed':[]})
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0
