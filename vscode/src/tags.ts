// Finding the uniscript tag at a column: `<:content>`, `\:name` and `\U1F60D`. The content starts with no space and has
// no brackets, braces, `;`, `=` or quotes, so Scala's `T <: Bound[…]>` and C++'s `<:` digraph are no tags.
const TAG = /<:(?:[^\s>][^>\n[\]{};="]*)?>|\\:(?:[Uu]\+)?[A-Za-z0-9_-]+|\\U[0-9A-Fa-f]{4,8}(?![A-Za-z0-9_-])/g;

export interface Tag {
	start: number;
	end: number;
	text: string;
}

/** The tag touching the column from either side */
export function tagAt(line: string, column: number): Tag | undefined {
	for (const match of line.matchAll(TAG)) {
		const end = match.index + match[0].length;
		if (match.index <= column && column <= end) return { start: match.index, end, text: match[0] };
	}
	return undefined;
}
