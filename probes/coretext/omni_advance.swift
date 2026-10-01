// Width of n consecutive hieroglyph groups as CoreText lays them out in the installed NewGardinerOmni:
// a font whose shaping gives up mid-run no longer grows by one group's width per group.
import CoreText
import Foundation

let groups = ["stack2": "\u{13000}\u{13430}\u{13050}", "stack3": "\u{133CF}\u{13430}\u{133CF}\u{13430}\u{133CF}"]
let font = CTFontCreateWithName("NewGardinerOmni" as CFString, 100, nil)
func width(_ text: String) -> Double {
	let attributed = NSAttributedString(string: text, attributes: [NSAttributedString.Key(kCTFontAttributeName as String): font])
	return CTLineGetTypographicBounds(CTLineCreateWithAttributedString(attributed), nil, nil, nil)
}
print(CTFontCopyFullName(font))
for (name, group) in groups.sorted(by: { $0.key < $1.key }) {
	let one = width(group)
	print(name, "one", Int(one), "ok n:", (1...8).filter { abs(width(String(repeating: group, count: $0)) - one * Double($0)) < 1 })
}
