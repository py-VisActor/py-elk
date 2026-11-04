"""Exercise source-tree host foundations. This does not execute layout."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pyelk.execution import create_context


def main():
    graph = {"id": "root", "children": [{"id": 2, "width": 40, "height": 30},
                                         {"id": "2", "width": 30, "height": 20}],
             "edges": [{"id": "e", "sources": [2], "targets": ["2"]}],
             "business": {"error": {"stack": "caller metadata"}, "$H": False}}
    constructor = {"defaultLayoutOptions": {"elk.direction": "LEFT"}}
    arguments = {"layoutOptions": {}}
    first = create_context(graph, constructor=constructor, layout_arguments=arguments)
    second = create_context(graph, constructor=constructor, layout_arguments=arguments)
    first.working_graph.node(2).set_property("selected", True)
    first.state["temporary"] = [2]
    print(json.dumps({"nodeIdsInOrder": [node.id for node in first.working_graph.nodes],
                      "directionAfterEmptyCallReplacement": first.resolved_options.values["org.eclipse.elk.direction"],
                      "callerInputPreserved": "selected" not in graph["children"][0],
                      "secondCallPreserved": second.working_graph.to_json() == graph and not second.state,
                      "layoutExecuted": False}, indent=2))


if __name__ == "__main__":
    main()
