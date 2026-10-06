#!/usr/bin/env python3
"""An exact name comes first in Sublime's list: \\:lang lists lang ⟨ above lAngle ⟪. Sublime re-sorts completions by
fuzzy score and by how often each was chosen before ("auto_complete_preserve_order": "some"), so while uniscript
completes a tag the view's setting is "strict", and outside tags the view's own value is back:
python3 tests/sublime/test_sublime_strict_order.py (sublime and sublime_plugin stubbed, the plugin imported as a package)"""
import importlib
import sys
import types
from pathlib import Path

ORDER_SETTING = "auto_complete_preserve_order"


class Region:
    def __init__(self, a, b=None):
        self.a, self.b = a, a if b is None else b

    def begin(self):
        return min(self.a, self.b)

    def empty(self):
        return self.a == self.b


class Settings(dict):
    def set(self, key, value):
        self[key] = value

    def erase(self, key):
        self.pop(key, None)


class View:
    def __init__(self, text):
        self.text, self.view_settings = text, Settings()

    def id(self):
        return 1

    def settings(self):
        return self.view_settings

    def sel(self):
        return [Region(len(self.text))]

    def line(self, point):
        return Region(self.text.rfind("\n", 0, point) + 1, point)

    def substr(self, region):
        if isinstance(region, int):
            return self.text[region:region + 1]
        return self.text[region.begin():region.b]

    def find(self, pattern, start, flags):
        return Region(self.text.find(pattern, start))

    def set_text(self, text):
        self.text = text


class CompletionItem:
    def __init__(self, trigger, annotation="", completion=""):
        self.trigger, self.annotation, self.completion = trigger, annotation, completion

    @classmethod
    def command_completion(cls, trigger, command, args, annotation=""):
        return cls(trigger, annotation, command)


class CompletionList:
    def __init__(self, items, flags=0):
        self.items, self.flags = items, flags


def stub_sublime():
    sublime = types.ModuleType("sublime")
    sublime.Region, sublime.CompletionItem, sublime.CompletionList = Region, CompletionItem, CompletionList
    sublime.load_settings = lambda name: Settings()
    sublime.status_message = print
    sublime.LITERAL = 1
    for flag in ("INHIBIT_WORD_COMPLETIONS", "INHIBIT_EXPLICIT_COMPLETIONS", "DYNAMIC_COMPLETIONS", "INHIBIT_REORDER"):
        setattr(sublime, flag, 0)
    plugin = types.ModuleType("sublime_plugin")
    for base in ("TextCommand", "WindowCommand", "EventListener", "ViewEventListener"):
        setattr(plugin, base, type(base, (), {}))
    plugin.all_callbacks = {"on_query_completions": []}
    plugin.view_event_listeners = {}
    sys.modules.update(sublime=sublime, sublime_plugin=plugin)


stub_sublime()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime"))
uniscript = importlib.import_module("Uniscript.uniscript")
listener = uniscript.UniscriptCompletionListener()

view = View("x \\:lang")
listed = listener.on_query_completions(view, "lang", [len(view.text)])
triggers = [item.trigger for item in listed.items]
assert triggers.index("lang") < triggers.index("lAngle"), triggers[:8]
assert view.settings()[ORDER_SETTING] == "strict", view.settings()

view.set_text("x lang")
assert listener.on_query_completions(view, "lang", [len(view.text)]) is None
assert ORDER_SETTING not in view.settings(), "outside tags the view's own order setting is back"
print("OK")
