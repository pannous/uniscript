#!/usr/bin/env python3
"""Inside <: and \\: tags the other packages' completions (All Autocomplete, LSP, …) are silenced, elsewhere they stay:
python3 tests/sublime/test_sublime_quiet_completions.py (sublime and sublime_plugin stubbed, the plugin imported as a package)"""
import importlib
import sys
import types
from pathlib import Path


class Region:
    def __init__(self, a, b=None):
        self.a, self.b = a, a if b is None else b

    def begin(self):
        return min(self.a, self.b)


class View:
    def __init__(self, text):
        self.text = text

    def id(self):
        return 1

    def line(self, point):
        return Region(self.text.rfind("\n", 0, point) + 1, point)

    def substr(self, region):
        return self.text[region.begin():region.b]


class Settings(dict):
    pass


def stub_sublime():
    sublime = types.ModuleType("sublime")
    sublime.Region = Region
    sublime.load_settings = lambda name: Settings()
    plugin = types.ModuleType("sublime_plugin")
    for base in ("TextCommand", "WindowCommand", "EventListener", "ViewEventListener"):
        setattr(plugin, base, type(base, (), {}))
    plugin.all_callbacks = {"on_query_completions": []}
    plugin.view_event_listeners = {}
    sys.modules.update(sublime=sublime, sublime_plugin=plugin)
    return plugin


def expect(actual, expected):
    assert actual == expected, "{!r} != {!r}".format(actual, expected)


sublime_plugin = stub_sublime()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sublime"))
uniscript = importlib.import_module("Uniscript.uniscript")


class WordsFromAllFiles(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        return ["reduce", "reden"]


class LanguageServer(sublime_plugin.ViewEventListener):
    def __init__(self, view):
        self.view = view

    def on_query_completions(self, prefix, locations):
        return ["redirect"]


in_tag, outside = View("x <:red"), View("x red")
words, server, ours = WordsFromAllFiles(), LanguageServer(in_tag), uniscript.UniscriptCompletionListener()
sublime_plugin.all_callbacks["on_query_completions"] += [words, ours]
sublime_plugin.view_event_listeners[1] = [server]

uniscript.silence_other_completions(in_tag)
uniscript.silence_other_completions(in_tag)  # wrapped once only
expect(words.on_query_completions(in_tag, "red", [7]), None)
expect(words.on_query_completions(outside, "red", [5]), ["reduce", "reden"])
expect(words.on_query_completions(View("\\:al"), "al", [4]), None)
expect(server.on_query_completions("red", [7]), None)
server.view = outside
expect(server.on_query_completions("red", [5]), ["redirect"])
assert ours.on_query_completions.__func__ is uniscript.UniscriptCompletionListener.on_query_completions, "ours stays"
print("OK")
