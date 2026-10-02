// Uniscript in VS Code, in every file type: completion inside `<:` and `\:` tags, the Unicode of a tag on hover, the
// quick fix "Replace with α", and the commands converting the selection or the file to Unicode and back
import * as vscode from "vscode";
import { readFileSync } from "node:fs";
import { EntityIndex, Uniscript } from "../../js/src/core.ts";
import { namesOf, suggestions, type Names, type Suggestion } from "./completion.ts";
import { tagAt } from "./tags.ts";

const INDEX_FILE = "entities.idx";
const ALL_DOCUMENTS: vscode.DocumentSelector = { pattern: "**" };
const TRIGGER_CHARACTERS = [":", " ", "-"];
const SETTINGS = "uniscript";
const INSERTS_SETTING = "completionInserts"; // "character": α in place of the tag, "name": <:alpha>
const TAG_END = ">";
const REOPEN_SUGGESTIONS: vscode.Command = { command: "editor.action.triggerSuggest", title: "" };
const ITEM_KINDS = {
	name: vscode.CompletionItemKind.Constant,
	group: vscode.CompletionItemKind.Folder,
	block: vscode.CompletionItemKind.Keyword,
};

let converter: Uniscript;
let index: EntityIndex;
let loadedNames: Names | undefined;
const names = () => (loadedNames ??= namesOf(index));

/** The Unicode of a tag, or undefined for block openers and what does not convert */
function unicodeOf(tag: string): string | undefined {
	try {
		return converter.convert(tag, "lenient").text || undefined;
	} catch {
		return undefined;
	}
}

function completionItem(suggestion: Suggestion, order: number, typed: string, replaced: vscode.Range, closedRange: vscode.Range, isShort: boolean) {
	const item = new vscode.CompletionItem({ label: suggestion.name, description: suggestion.detail }, ITEM_KINDS[suggestion.kind]);
	// the typed text, spaces and all, then the rest of the name: VS Code filters by the text the item replaces
	item.filterText = typed + suggestion.written.slice(typed.length);
	item.sortText = String(order).padStart(5, "0");
	item.insertText = suggestion.written;
	item.range = replaced;
	if (suggestion.kind !== "name") {
		item.command = REOPEN_SUGGESTIONS;
	} else if (vscode.workspace.getConfiguration(SETTINGS).get(INSERTS_SETTING) === "character") {
		const tag = suggestion.written.endsWith(TAG_END) || isShort ? suggestion.written : suggestion.written + TAG_END;
		const unicode = unicodeOf(tag);
		if (unicode) {
			item.insertText = unicode;
			item.range = closedRange;
			item.detail = tag;
		}
	}
	return item;
}

const completionProvider: vscode.CompletionItemProvider = {
	provideCompletionItems(document, position) {
		const line = document.lineAt(position).text;
		const next = line.charAt(position.character);
		const found = suggestions(line.slice(0, position.character), next, names());
		if (!found?.items.length) return undefined;
		const start = position.with({ character: found.tagStart });
		const closedEnd = next === TAG_END && !found.isShort ? position.translate(0, 1) : position;
		const typed = line.slice(found.tagStart, position.character);
		const items = found.items.map((suggestion, order) =>
			completionItem(suggestion, order, typed, new vscode.Range(start, position), new vscode.Range(start, closedEnd), found.isShort));
		return new vscode.CompletionList(items, true); // incomplete: asked again while typing, the groups change
	},
};

function tagUnderCursor(document: vscode.TextDocument, position: vscode.Position) {
	const tag = tagAt(document.lineAt(position).text, position.character);
	const unicode = tag && unicodeOf(tag.text);
	return tag && unicode ? { range: new vscode.Range(position.line, tag.start, position.line, tag.end), unicode } : undefined;
}

const hoverProvider: vscode.HoverProvider = {
	provideHover(document, position) {
		const tag = tagUnderCursor(document, position);
		if (!tag) return undefined;
		const codePoints = [...tag.unicode].map((character) => "U+" + character.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0"));
		return new vscode.Hover(new vscode.MarkdownString(`**${tag.unicode}**  ${codePoints.join(" ")}`), tag.range);
	},
};

const codeActionProvider: vscode.CodeActionProvider = {
	provideCodeActions(document, range) {
		const tag = tagUnderCursor(document, range.start);
		if (!tag) return undefined;
		const action = new vscode.CodeAction(`Replace with ${tag.unicode}`, vscode.CodeActionKind.QuickFix);
		action.edit = new vscode.WorkspaceEdit();
		action.edit.replace(document.uri, tag.range, tag.unicode);
		return [action];
	},
};

/** Replaces the non-empty selections, else the whole document, with their conversion */
async function convertEditor(convert: (text: string) => string) {
	const editor = vscode.window.activeTextEditor;
	if (!editor) return;
	const { document } = editor;
	const selected = editor.selections.filter((selection) => !selection.isEmpty);
	const ranges = selected.length ? selected : [new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length))];
	await editor.edit((edit) => ranges.forEach((range) => edit.replace(range, convert(document.getText(range)))));
}

function toUnicode(text: string): string {
	const { text: converted, warnings } = converter.convert(text, "lenient");
	if (warnings.length) vscode.window.setStatusBarMessage(`uniscript: ${warnings.map((warning) => warning.message).join("; ")}`, 10000);
	return converted;
}

export function activate(context: vscode.ExtensionContext) {
	index = new EntityIndex(readFileSync(context.asAbsolutePath(INDEX_FILE)));
	converter = new Uniscript(index);
	context.subscriptions.push(
		vscode.languages.registerCompletionItemProvider(ALL_DOCUMENTS, completionProvider, ...TRIGGER_CHARACTERS),
		vscode.languages.registerHoverProvider(ALL_DOCUMENTS, hoverProvider),
		vscode.languages.registerCodeActionsProvider(ALL_DOCUMENTS, codeActionProvider, { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }),
		vscode.commands.registerCommand("uniscript.toUnicode", () => convertEditor(toUnicode)),
		vscode.commands.registerCommand("uniscript.toUniscript", () => convertEditor((text) => converter.toUniscript(text))),
	);
}

export function deactivate() {}
