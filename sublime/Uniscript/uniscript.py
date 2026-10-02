"""Sublime Text commands that replace uniscript (<:alpha> <:fracture A>) with Unicode (α 𝔄) and back, and completion of
names inside <: and \\: tags in every file type."""
import sublime
import sublime_plugin

# helpers are looked up at call time: Sublime reloads a changed uniscript_cli.py in place, names imported from it would
# keep the old functions and classes
from . import uniscript_cli as cli

SETTINGS_FILE = "Uniscript.sublime-settings"
LIVE_SETTING = "convert_while_typing"  # true, false, or "header": only in files starting with <:
LIVE_IN_UNISCRIPT_FILES = "header"
TYPED_COMMAND = "insert"
COMMITTED_COMMANDS = ("commit_completion", "insert_completion")
TAG_END = ">"
TAG_OPENERS = ("<:", "\\:")
CONTINUE_AFTER = ("-", " ")  # a committed group or block word asks for the rest
QUIET_SETTING = "only_uniscript_completions_in_tags"
QUERY_CALLBACK = "on_query_completions"
QUIETED_MARK = "_uniscript_quieted"
_names = None


def settings():
    return sublime.load_settings(SETTINGS_FILE)


def selected_or_whole(view):
    """The non-empty selections, else the whole buffer"""
    return [region for region in view.sel() if not region.empty()] or [sublime.Region(0, view.size())]


def names():
    """The index's names, from the CLI once per session"""
    global _names
    if _names is None:
        _names = cli.load_names(settings().get("binary", ""))
    return _names


def text_before_cursor(view, cursor, length=None):
    start = view.line(cursor).begin() if length is None else max(0, cursor - length)
    return view.substr(sublime.Region(start, cursor))


def is_typing_tag(view, point):
    return cli.TYPED_TAG.search(text_before_cursor(view, point)) is not None


def quieted(listener, query):
    """The listener's on_query_completions, answering nothing while a uniscript tag is typed"""
    def quiet_query(*args):
        view = listener.view if isinstance(listener, sublime_plugin.ViewEventListener) else args[0]
        locations = args[-1]
        if settings().get(QUIET_SETTING, True) and is_typing_tag(view, locations[0]):
            return None
        return query(*args)
    setattr(quiet_query, QUIETED_MARK, True)
    return quiet_query


def silence_other_completions(view):
    """Sublime merges every package's completions and has no flag against other plugins' lists, so the other
    listeners (All Autocomplete, LSP, …) are wrapped: inside <: and \\: tags they stay quiet. Uses sublime_plugin's
    listener registries (all_callbacks, view_event_listeners), undocumented but stable since ST3; listeners loaded
    later are wrapped at the next query."""
    registered = getattr(sublime_plugin, "all_callbacks", {}).get(QUERY_CALLBACK, [])
    per_view = getattr(sublime_plugin, "view_event_listeners", {}).get(view.id(), [])
    for listener in list(registered) + list(per_view):
        query = getattr(listener, QUERY_CALLBACK, None)
        if query is None or isinstance(listener, UniscriptCompletionListener) or getattr(query, QUIETED_MARK, False):
            continue
        setattr(listener, QUERY_CALLBACK, quieted(listener, query))


def report(view, warnings):
    if warnings:
        view.window().status_message("uniscript: " + "; ".join(warnings))


class UniscriptConvertCommand(sublime_plugin.TextCommand):
    """Replaces the regions (default: the selections or the whole file) with their conversion. While typing (live),
    errors go to the status bar and a tag converting to nothing (a block opener like <:greek>) stays as typed."""

    def run(self, edit, reverse=False, regions=None, live=False):
        targets = [sublime.Region(*region) for region in regions] if regions else selected_or_whole(self.view)
        warnings = []
        try:
            for region in sorted(targets, key=lambda region: region.begin(), reverse=True):
                converted, region_warnings = cli.convert(self.view.substr(region), reverse, settings().get("binary", ""))
                if converted or not live:
                    self.view.replace(edit, region, converted)
                warnings += region_warnings
        except cli.UniscriptError as error:
            if live:
                return self.view.window().status_message("uniscript: {}".format(error))
            return sublime.error_message("uniscript: {}".format(error))
        report(self.view, warnings)


class UniscriptWhileTypingListener(sublime_plugin.ViewEventListener):
    """Replaces a tag as soon as its closing > is typed: <:alpha> becomes α"""

    def is_live(self):
        live = settings().get(LIVE_SETTING, LIVE_IN_UNISCRIPT_FILES)
        if live == LIVE_IN_UNISCRIPT_FILES:
            return cli.is_uniscript_file(self.view.substr(sublime.Region(0, 2)))
        return bool(live)

    def on_post_text_command(self, command_name, args):
        typed = (args or {}).get("characters", "") if command_name == TYPED_COMMAND else ""
        committed = command_name in COMMITTED_COMMANDS
        before = text_before_cursor(self.view, self.view.sel()[0].b, 2) if len(self.view.sel()) else ""
        if typed and before in TAG_OPENERS or committed and before[-1:] in CONTINUE_AFTER:
            silence_other_completions(self.view)
            return self.view.run_command("auto_complete", {"disable_auto_insert": True})
        if not (typed.endswith(TAG_END) or committed and before.endswith(TAG_END)) or not self.is_live():
            return
        regions = []
        for cursor in (region.b for region in self.view.sel() if region.empty()):
            line_start = self.view.line(cursor).begin()
            offset = cli.tag_before_cursor(self.view.substr(sublime.Region(line_start, cursor)))
            if offset is not None:
                regions.append((line_start + offset, cursor))
        if regions:
            self.view.run_command("uniscript_convert", {"regions": regions, "live": True})


class UniscriptCompletionListener(sublime_plugin.EventListener):
    """Inside <: and \\: tags in any file: entity names with their character, block words, after block words their
    operands; names sharing their next segment fold into one group (alchemical-)"""

    def on_query_completions(self, view, prefix, locations):
        cursor = locations[0]
        line = text_before_cursor(view, cursor)
        if not any(opener in line for opener in TAG_OPENERS):
            return None
        silence_other_completions(view)
        try:
            entries = cli.completions(line, view.substr(cursor), names())
        except cli.UniscriptError as error:
            view.window().status_message("uniscript: {}".format(error))
            return None
        if not entries:
            return None
        items = [sublime.CompletionItem(trigger, annotation=annotation, completion=completion) for trigger, annotation, completion in entries]
        flags = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.DYNAMIC_COMPLETIONS
        return sublime.CompletionList(items, flags)
