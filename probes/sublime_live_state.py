# Copy into Sublime's Packages/User to see the running plugin's state (Packages/Uniscript is reloaded in place); it
# writes probes/sublime_live_state.json on load. Remove it from Packages/User afterwards.
import sys, json
def plugin_loaded():
    plugin = sys.modules["Uniscript.uniscript"]
    cli = sys.modules["Uniscript.uniscript_cli"]
    entries = cli.completions("\\:wo", "", plugin.names(), "wo", plugin.inserts_characters())
    items = [plugin.completion_item(t, a, c, "wo", w) for t, a, c, w in entries[:3]]
    state = [[i.trigger, i.annotation] for i in items]
    open("/Users/me/dev/uniscript/probes/sublime_live_state.json", "w").write(json.dumps(state, ensure_ascii=False))
