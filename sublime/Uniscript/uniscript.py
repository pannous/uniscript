"""Sublime Text commands that replace uniscript (<:alpha> <:fracture A>) with Unicode (α 𝔄) and back."""
import sublime
import sublime_plugin

from .uniscript_cli import UniscriptError, convert, is_uniscript_file, tag_before_cursor

SETTINGS_FILE = "Uniscript.sublime-settings"
LIVE_SETTING = "convert_while_typing"  # true, false, or "header": only in files starting with <:
LIVE_IN_UNISCRIPT_FILES = "header"
TYPED_COMMAND = "insert"
TAG_END = ">"


def settings():
    return sublime.load_settings(SETTINGS_FILE)


def selected_or_whole(view):
    """The non-empty selections, else the whole buffer"""
    return [region for region in view.sel() if not region.empty()] or [sublime.Region(0, view.size())]


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
                converted, region_warnings = convert(self.view.substr(region), reverse, settings().get("binary", ""))
                if converted or not live:
                    self.view.replace(edit, region, converted)
                warnings += region_warnings
        except UniscriptError as error:
            if live:
                return self.view.window().status_message("uniscript: {}".format(error))
            return sublime.error_message("uniscript: {}".format(error))
        report(self.view, warnings)


class UniscriptWhileTypingListener(sublime_plugin.ViewEventListener):
    """Replaces a tag as soon as its closing > is typed: <:alpha> becomes α"""

    def is_live(self):
        live = settings().get(LIVE_SETTING, LIVE_IN_UNISCRIPT_FILES)
        if live == LIVE_IN_UNISCRIPT_FILES:
            return is_uniscript_file(self.view.substr(sublime.Region(0, 2)))
        return bool(live)

    def on_post_text_command(self, command_name, args):
        typed = (args or {}).get("characters", "")
        if command_name != TYPED_COMMAND or not typed.endswith(TAG_END) or not self.is_live():
            return
        regions = []
        for cursor in (region.b for region in self.view.sel() if region.empty()):
            line_start = self.view.line(cursor).begin()
            offset = tag_before_cursor(self.view.substr(sublime.Region(line_start, cursor)))
            if offset is not None:
                regions.append((line_start + offset, cursor))
        if regions:
            self.view.run_command("uniscript_convert", {"regions": regions, "live": True})
