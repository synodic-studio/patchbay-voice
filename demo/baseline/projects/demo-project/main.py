"""A tiny in-memory widget store, used by the Patchbay Voice demo."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Widget Store")

widgets: dict[int, dict] = {}
_next_id = 1


@app.get("/widgets")
def list_widgets() -> list[dict]:
    return list(widgets.values())


@app.get("/widgets/{widget_id}")
def get_widget(widget_id: int) -> dict:
    if widget_id not in widgets:
        raise HTTPException(404, "widget not found")
    return widgets[widget_id]


@app.post("/widgets")
def create_widget(name: str) -> dict:
    global _next_id
    widget = {"id": _next_id, "name": name}
    widgets[_next_id] = widget
    _next_id += 1
    return widget


@app.delete("/widgets/{widget_id}")
def delete_widget(widget_id: int) -> dict:
    if widgets.pop(widget_id, None) is None:
        raise HTTPException(404, "widget not found")
    return {"deleted": widget_id}
