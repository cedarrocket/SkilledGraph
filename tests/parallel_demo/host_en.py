from skilledgraph import build_graph


def main(graph_path, argv):
    if argv:
        raise ValueError("No arguments expected")
    builder = build_graph(graph_path)
    builder.add_edge("Start", "Left")
    builder.add_edge("Start", "Right")
    builder.add_edge("Right", "RightLast")
    # A native waiting edge waits for both branch ends, including unequal lengths.
    builder.add_edge(["Left", "RightLast"], "Join")
    result = builder.compile().invoke({"events": []})
    events = result["events"]
    origin = events[0]["at"]
    for event in events:
        if "start" in event:
            print(f'{event["node"]}: {event["start"] - origin:.3f}s -> {event["end"] - origin:.3f}s')
        else:
            print(f'{event["node"]}: {event["at"] - origin:.3f}s')
    branches = {e["node"]: e for e in events if "start" in e}
    overlap = max(branches[n]["start"] for n in ("Left", "Right")) < min(branches[n]["end"] for n in ("Left", "Right"))
    print(f"Left/Right overlap: {overlap}")
    print(result["summary"])
    return 0
