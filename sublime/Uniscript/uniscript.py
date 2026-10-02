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
INSERTS_SETTING = "completion_inserts"  # "character": a chosen name becomes its character, "name": <:alpha> stays
INSERTS_CHARACTERS = "character"
QUERY_CALLBACK = "on_query_completions"
QUIETED_MARK = "_uniscript_quieted"
NO_MATCH_REGION = "uniscript_no_match"
NO_MATCH_SCOPE = "invalid"  # the color scheme's error color
NO_MATCH_BLINKS = 2
NO_MATCH_BLINK_MS = 150
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


def inserts_characters():
    return settings().get(INSERTS_SETTING, INSERTS_CHARACTERS) == INSERTS_CHARACTERS


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
        if not len(self.view.sel()):
            return
        if command_name in COMMITTED_COMMANDS:
            return finish_completion(self.view)
        typed = (args or {}).get("characters", "") if command_name == TYPED_COMMAND else ""
        if typed and text_before_cursor(self.view, self.view.sel()[0].b, 2) in TAG_OPENERS:
            open_completions(self.view)
        elif typed.endswith(TAG_END) and self.is_live():
            convert_tags_before_cursors(self.view, cli.tag_before_cursor)


def open_completions(view):
    silence_other_completions(view)
    view.run_command("auto_complete", {"disable_auto_insert": True})


def convert_tags_before_cursors(view, find_tag):
    """Converts the tags ending at the cursors, found in their line by find_tag (the tag's offset or None)"""
    regions = []
    for cursor in (region.b for region in view.sel() if region.empty()):
        line_start = view.line(cursor).begin()
        offset = find_tag(view.substr(sublime.Region(line_start, cursor)))
        if offset is not None:
            regions.append((line_start + offset, cursor))
    if regions:
        view.run_command("uniscript_convert", {"regions": regions, "live": True})


def finish_completion(view):
    """After a chosen completion: a group or block word asks for the rest, a name becomes its character"""
    before = text_before_cursor(view, view.sel()[0].b, 1)
    if before in CONTINUE_AFTER:
        open_completions(view)
    elif inserts_characters():
        convert_tags_before_cursors(view, cli.finished_tag_before_cursor)  # \\:equal-to-by-definition becomes ≝


def blink(view, region, times=NO_MATCH_BLINKS):
    """Flashes the region in the error color: the editor's way to say no (Sublime has no bell)"""
    view.add_regions(NO_MATCH_REGION, [region], NO_MATCH_SCOPE)
    sublime.set_timeout(lambda: view.erase_regions(NO_MATCH_REGION), NO_MATCH_BLINK_MS)
    if times > 1:
        sublime.set_timeout(lambda: blink(view, region, times - 1), 2 * NO_MATCH_BLINK_MS)


class UniscriptTabCompletionCommand(sublime_plugin.TextCommand):
    """Tab in a tag while the popup is closed (Default.sublime-keymap), instead of Sublime's own Tab completion, which
    picks one by its own ranking (equiv over equal): the only match is inserted, several open the list (then Tab
    commits its top, the whole name if typed), none blink"""

    def run(self, edit):
        cursor = self.view.sel()[0].b
        line = text_before_cursor(self.view, cursor)
        best = cli.tab_completion(line, self.view.substr(cursor), names(), inserts_characters())
        if best == cli.CHOOSE:
            return open_completions(self.view)
        if best is None:  # nothing to complete: no tab either, the name blinks
            typed = cli.typed_tag(line, names())[3]
            blink(self.view, sublime.Region(cursor - len(typed), cursor))
            return self.view.window().status_message("uniscript: no name starts with {}".format(typed))
        replaced, text = best
        self.view.replace(edit, sublime.Region(cursor - replaced, cursor), text)
        finish_completion(self.view)


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
            entries = cli.completions(line, view.substr(cursor), names(), prefix, inserts_characters())
        except cli.UniscriptError as error:
            view.window().status_message("uniscript: {}".format(error))
            return None
        if not entries:
            return None
        items = [sublime.CompletionItem(trigger, annotation=annotation, completion=completion) for trigger, annotation, completion in entries]
        flags = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.DYNAMIC_COMPLETIONS
        return sublime.CompletionList(items, flags)
