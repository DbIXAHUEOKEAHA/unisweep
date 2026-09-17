# Per-point script: one ASC500 coarse Y step after every master-axis step.

ASC_ADDRESS = "COM3"
STEPS = 5

# The script namespace is rebuilt for every point, so anything that has to
# survive to the next point lives on the engine.
S = engine.__dict__.setdefault("_asc_coarse_y", {})

master = engine._loop_axes[0]           # outermost axis = the slow one
here = float(values[master])
previous = S.get("at")

if previous is None:
    S["at"] = here                      # first master position, nothing to do

elif here != previous:
    S["at"] = here                      # advance first: never step twice
    adapter = S.get("adapter")
    if adapter is None:
        # 'devices' holds only the swept axes, so the ASC500 comes from
        # the registry instead.
        adapter = (engine.registry.connected(ASC_ADDRESS)
                   or engine.registry.connect(ASC_ADDRESS))
        S["adapter"] = adapter
    adapter.set("step_up_y", STEPS)
