<:uniscript version="https://uniscript.org/v1">
<:alpha> <:beta> <:gamma>: this file starts with the uniscript marker, so MarkdownPreview converts uniscript in its prose.


Quick check of **GitHub-flavoured** Markdown: *emphasis*, ~~strikethrough~~, `inline code`, and an autolink https://github.com.

<!-- \:1F60D TODO Disable! -->
\:U1F60D
\:0x1F60D
<!-- \:U+1F60D NO, OK -->
<!-- \U1F60D NO, OK-->

<:eg A1>|<:gardiner A1C>  𓀀|󳀃  

# Uniscript in <:fracture M>arkdown

## Unknown entities stay visible

Neither <:nosuchthing> nor \:nosuchthing is an entity.
    <!-- Deliberately not quote them to see that the editor handles it well.  -->

## Unsupported characters are kept and marked

No `<:greek c>` <:greek c>, red may not color `<:red 𓀀>` <:red 𓀀>, no beside group of `<:beside a b>` <:beside a b>.
<:reverse gardiner AB> | <:gardiner AB>

## Code is left alone, except wasp and warp

Inline `<:alpha> \:infinity` stays as written, and so do code blocks:

```
<:alpha> \:infinity <:fracture A>
```

    <:beta> in an indented block

Except in wasp and warp, where uniscript is part of the language:

```wasp
circle := <:pi> * r<:upper 2>  // \:infinity <:nosuchthing> <:greek c>
```

## Wiki examples

- `\:infinity` → \:infinity
- `<:fracture A>` → <:fracture A>
- `<:fracture A b c >` → <:fracture A b c >
- `<:fracture> A b c <:>` → <:fracture> A b c <:>
- `<:greek> a b g d phi<:/greek>` → <:greek> a b g d phi<:/greek>
- `<:greek> athos <:/greek> <:greek eta Omega>` → <:greek> athos <:/greek> <:greek eta Omega>
- `x<:upper a> X<:upper A>` → x<:upper a> X<:upper A>
- `<:ligature ae>` → <:ligature ae>
- `<:red circle> <:brown heart>` → <:red circle> <:brown heart>
- `<:reverseInPlace e>` → <:reverseInPlace e>
- `<:iconic ⚠>` → <:iconic ⚠>
- `<:mirror red A>` → <:mirror red A>
- `<:forall> x <:in> <:double R>` → <:forall> x <:in> <:double R>
- `<:beside 犭 句>` → <:beside 犭 句>
- `<:above 𓀀 𓁐>  <:reverse 𓀀 𓁐>` → <:above 𓀀 𓁐>  <:reverse 𓀀 𓁐>
- `<:above 󳀃 𓁐>  <:reverse 󳀃 𓁐>` → <:above 󳀃 𓁐>  <:reverse 󳀃 𓁐>
- `a literal <<::> marker` → a literal <<::> marker
<:woman><:zwj><:emoji-component-red-hair>
<:woman><:zwj><:emoji-component-red-hair>


**Bold <:alpha>**, *italic <:Omega>* and a [link to <:infinity>](https://example.com).

| uniscript | Unicode |
|---|---|
| `<:double R>` | <:double R> |
| `<:greek bold alpha>` | <:greek small letter alpha> |