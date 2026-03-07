from collections import defaultdict
from datetime import datetime
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich import box
from db import next_task

# Rolling cycle log: list of {action, tools: [{name, input, result}]}
_cycles = []

STATUS_COLORS = {
    "monitoring": "dim",
    "working":    "green",
    "message":    "yellow",
}

def push_cycle(action, tool_log):
    _cycles.append({"action": action, "tools": list(tool_log)})
    if len(_cycles) > 50:
        _cycles.pop(0)

def _header(status, last_action):
    color = STATUS_COLORS.get(status, "white")
    ts = datetime.utcnow().strftime("%H:%M:%S UTC")
    return Panel(
        Text.from_markup(f"[{color}][{status.upper()}][/{color}]  {last_action}  [dim]{ts}[/dim]"),
        title="[bold]Chief of Staff[/bold]",
        box=box.ROUNDED,
    )

def _tasks_panel(conn):
    rows = conn.execute(
        "SELECT id, priority, effort, title, status, assigned_to FROM tasks "
        "WHERE status NOT IN ('done') ORDER BY urgent DESC, priority ASC, id ASC LIMIT 20"
    ).fetchall()

    t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    t.add_column("#",      width=4)
    t.add_column("P",      width=2)
    t.add_column("effort", width=7)
    t.add_column("agent",  width=5)
    t.add_column("title")
    t.add_column("status", width=10)

    for r in rows:
        status_color = {"pending": "dim", "in_progress": "green", "deferred": "yellow"}.get(r["status"], "dim")
        t.add_row(
            str(r["id"]),
            str(r["priority"]),
            r["effort"] or "",
            (r["assigned_to"] or "cos")[:4],
            r["title"],
            f"[{status_color}]{r['status']}[/{status_color}]",
        )

    return Panel(t, title="[bold]Tasks[/bold]", box=box.ROUNDED)

def _log_panel():
    if not _cycles:
        return Panel("[dim]No cycles yet.[/dim]", title="[bold]Activity Log[/bold]", box=box.ROUNDED)

    tree = Tree("[bold]Recent cycles[/bold]")
    for cycle in reversed(_cycles[-10:]):
        branch = tree.add(f"[cyan]{cycle['action']}[/cyan]")
        grouped = defaultdict(list)
        for entry in cycle["tools"]:
            grouped[entry["name"]].append(entry)
        for name, entries in grouped.items():
            tool_node = branch.add(f"[yellow]{name}[/yellow] x{len(entries)}")
            for e in entries:
                result_preview = str(e["result"])[:80].replace("\n", " ")
                tool_node.add(f"[dim]{result_preview}[/dim]")

    return Panel(tree, title="[bold]Activity Log[/bold]", box=box.ROUNDED)

def build_layout(conn, status="monitoring", last_action=""):
    layout = Layout()
    layout.split_column(
        Layout(_header(status, last_action), size=3),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(_tasks_panel(conn), name="tasks", ratio=1),
        Layout(_log_panel(),       name="log",   ratio=1),
    )
    return layout
