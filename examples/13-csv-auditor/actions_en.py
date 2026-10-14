import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
import json
from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage, HumanMessage


class State(MessagesState):
    csv_path: str
    metrics: dict
    report: dict
    attempts: int
    validation: str


def load(state):
    with open(state["csv_path"], encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"id", "amount", "customer"} <= set(reader.fieldnames or []):
            raise ValueError("CSV requires id, amount, customer columns")
        rows = list(reader)
    ids = Counter(row.get("id", "") for row in rows if row.get("id"))
    total = Decimal(0)
    invalid = []
    for number, row in enumerate(rows, 2):
        try:
            value = Decimal(row.get("amount") or "")
            if not value.is_finite():
                raise InvalidOperation
            total += value
        except InvalidOperation:
            invalid.append(number)
    return {"metrics": {"rows": len(rows), "valid_total": str(total),
                        "duplicate_ids": sorted(k for k, n in ids.items() if n > 1), "invalid_rows": invalid,
                        "missing_customer_rows": [i for i, row in enumerate(rows, 2) if not row.get("customer")]}}


def materials(state):
    return state["metrics"]


def validate(state):
    attempt = state.get("attempts", 0) + 1
    try:
        report = json.loads(state["messages"][-1].text)
        valid = (all(report.get(k) == state["metrics"][k] for k in ("rows", "valid_total", "duplicate_ids", "invalid_rows"))
                 and isinstance(report.get("actions"), list) and bool(report["actions"])
                 and all(isinstance(item, str) for item in report["actions"]))
    except (ValueError, AttributeError, TypeError):
        report, valid = {}, False
    status = "valid" if valid else "retry" if attempt < 3 else "failed"
    update = {"attempts": attempt, "validation": status, "report": report}
    if status == "retry":
        update["messages"] = [HumanMessage(content="JSON or metric validation failed. Copy metric values/types exactly and output a nonempty actions list.")]
    return update


def route(state):
    return state["validation"]


def render(state):
    report = state["report"]
    return {"messages": [AIMessage(content=f'Total: {report["rows"]} rows; parseable amount total {report["valid_total"]} (not deduplicated).\nDuplicate IDs: {report["duplicate_ids"]}; invalid-amount rows: {report["invalid_rows"]}.\nSuggestions: ' + "；".join(report["actions"]))]}


def failure(state):
    return {"messages": [AIMessage(content="Repeated metric validation failed; use original metrics instead of the model report.") ]}
