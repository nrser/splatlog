---
name: Master syntax styles
overview: Define splatlog's master styles as a Pygments Style subclass (ansi* colors) covering common code/runtime elements, then generate the Rich Theme's syntax-ish entries (routine.*, log.*, inspect.*, repr.*, json.*) from it via a token map + custom ansi->Rich bridge, so shared concepts stay consistent and inherit Pygments' fallback for free.
todos:
  - id: tokens
    content: Define custom Pygments Token subtypes for splatlog extensions (method/classmethod/staticmethod under Name.Function, path/filename) in a new splatlog/rich/syntax_styles.py module.
    status: pending
  - id: master-style
    content: Define SplatlogStyle (Pygments Style subclass) with styles keyed on tokens using ansi* color names, covering Name.Class/Function/Attribute/Namespace/Variable/Constant, Keyword, String, Number, plus the custom tokens.
    status: pending
  - id: bridge
    content: Write an ansi*->Rich-name bridge that resolves a token (walking parents on miss) to a Rich Style, preserving ANSI names so override_ansi_colors keeps working; generalize the existing to_theme SyntaxTheme branch to reuse it.
    status: pending
  - id: token-map
    content: Define STYLE_TOKENS mapping theme style names (routine.*, log.class/funcName/data.*, inspect.*, repr.*, json.*) to tokens, and a builder that generates those Theme entries from the master Style.
    status: pending
  - id: rebuild-theme
    content: Rebuild THEME in theme.py to merge hand-defined non-syntax entries (datetime, timedelta, report, log.level/name/label, routine.sep/call/icon) with generated syntax entries; keep THEME_ANSI_DARK via override_ansi_colors.
    status: pending
  - id: enrich-constants
    content: Repoint mis-namespaced style-name constants in enrich/typ.py and enrich/path.py to semantically-correct (now generated) names.
    status: pending
  - id: docs
    content: Update the THEME docstring to describe the Pygments-backed master, token map, and ansi bridge.
    status: pending
  - id: demo
    content: Add dev/notes/2026-07-22.pygments-master-styles.ipynb + a doctest showing derived names share the master token's style and that a custom subtype falls back to its parent.
    status: pending
  - id: verify
    content: Run poe test and poe check; fix any doctest/type failures.
    status: pending
isProject: false
---

# Pygments-Backed Master Styles

Pivot: instead of ad-hoc `Style` constants, model splatlog's master styles as a **Pygments `Style` subclass** keyed on the Pygments token tree, and **generate** the Rich `Theme`'s syntax-ish entries from it. We get Pygments' format, tested inheritance/fallback (`Number.Bin` -> `Number` -> `Token`), and trivial extension via new `Token.X.Y` subtypes. Scope stays internal (no new public API); our default palette uses Pygments `ansi*` color names bridged back to Rich ANSI names so `override_ansi_colors` / `PALETTE_ANSI_DARK` / `THEME_ANSI_DARK` keep working unchanged.

## Why this shape

Today `THEME` is a flat `dict[str, Style]` where one concept is styled inconsistently across namespaces:

- `routine.class`: `Style(color="magenta", bold=True)`
- `log.class`: `Style(color="yellow", dim=True)`
- `inspect.class` (Rich default): `Style(italic=True, color="bright_cyan")`
- `repr.tag_name` (Rich default): `Style(color="bright_magenta", bold=True)`

We make one Pygments token (`Name.Class`) the single source of truth and generate all four from it. Pygments' `StyleMeta` resolves inheritance at class-creation, so we author only the tokens we care about and every subtype falls back automatically.

## New module: `splatlog/rich/syntax_styles.py`

Keeps `theme.py` (already 626 lines) focused; this module is independently testable.

### 1. Custom tokens (extensions)

```python
from pygments.token import Name, Keyword, String, Number, Token

# Method kinds fall back to Name.Function
METHOD = Name.Function.Method
CLASSMETHOD = Name.Function.Classmethod
STATICMETHOD = Name.Function.Staticmethod

# Filesystem paths fall back to Name
PATH = Name.Path
FILENAME = Name.Path.Filename
```

Because `_TokenType.__getattr__` auto-creates subtypes and sets `.parent`, these need no registration — just declaration in the master `styles` dict (even with `""`) so they land in `_styles` and inherit.

### 2. Master `SplatlogStyle` (Pygments `Style` subclass)

`styles` keyed on tokens, values in Pygments' mini-language using `ansi*` names (so the bridge can map them back to Rich ANSI names). Draws initial values from the current theme so nothing visibly regresses; ambiguous cases (below) are chosen for consistency. Sketch:

```python
class SplatlogStyle(PygmentsStyle):
    styles = {
        Name.Namespace:  "ansiblue",              # module path segments
        Name.Class:      "ansimagenta bold",      # classes & types
        Name.Function:   "ansicyan italic",       # plain functions
        METHOD:          "ansiblue italic",       # instance methods
        CLASSMETHOD:     "",                       # inherit Function
        STATICMETHOD:    "",                       # inherit Function
        Name.Attribute:  "ansiyellow",            # attrs / keys
        Name.Variable:   "",                       # identifiers
        Keyword.Constant:"ansimagenta italic",    # True/False/None
        Keyword:         "ansiyellow bold",
        String:          "ansigreen",
        Number:          "ansicyan bold",
        PATH:            "ansimagenta",
        FILENAME:        "ansibrightmagenta",
    }
```

### 3. `ansi*` -> Rich Style bridge

Pygments `Style.style_for_token(t)` returns a dict with both `color` (hex) and `ansicolor` (name, e.g. `"ansibrightmagenta"`) plus `bold`/`italic`/`underline`. We build a Rich `Style`, preferring the ANSI name (mapped to Rich's naming) so `override_ansi_colors` still applies:

- Map table (16 entries): `ansiblack->black`, ... `ansimagenta->magenta`, `ansigray->white`, `ansibrightblack->bright_black`, ... `ansiwhite->bright_white`.
- If `ansicolor` is set, use the mapped Rich name; else fall back to the hex `color` (so external hex themes like `monokai` still bridge as truecolor).
- Resolution walks `token.split()` from specific to general on `KeyError`, so undeclared tokens (and external themes lacking our custom subtypes) still resolve to the nearest ancestor.

This same bridge generalizes the hand-rolled token mapping already living in `to_theme`'s `SyntaxTheme` branch ([theme.py](splatlog/rich/theme.py) ~L524-552) — refactor it to reuse the bridge + token map.

### 4. Token map + builder

```python
STYLE_TOKENS: dict[str, TokenType] = {
    "routine.module": Name.Namespace,
    "routine.class": Name.Class,
    "routine.function": Name.Function,
    "routine.method": METHOD,
    "routine.classmethod": CLASSMETHOD,
    "routine.staticmethod": STATICMETHOD,
    "routine.locals": Name.Variable,
    "log.class": Name.Class,          # currently also dim; see below
    "log.funcName": Name.Function,
    "log.data.name": Name.Attribute,
    "log.data.type": Name.Class,
    "inspect.class": Name.Class,
    "inspect.def": Name.Function,
    "inspect.async_def": Name.Function,
    "inspect.attr": Name.Attribute,
    "inspect.attr.dunder": Name.Attribute,   # + dim modifier
    "repr.tag_name": Name.Class,
    "repr.attrib_name": Name.Attribute,
    "repr.call": Name.Function,
    "repr.str": String, "json.str": String,
    "repr.number": Number, "repr.number_complex": Number, "json.number": Number,
    "repr.bool_true": Keyword.Constant, "repr.bool_false": Keyword.Constant,
    "repr.none": Keyword.Constant, "json.null": Keyword.Constant,
    "json.bool_true": Keyword.Constant, "json.bool_false": Keyword.Constant,
    "json.key": Name.Attribute,
    "repr.path": PATH, "repr.filename": FILENAME,
}
```

`build_syntax_styles(style=SplatlogStyle) -> dict[str, Style]` resolves each entry through the bridge. A small per-name modifier hook applies context tweaks that aren't part of the token's identity (e.g. `log.*` add `dim`, `inspect.attr.dunder` adds `dim`) via `Style + Style(...)`.

Judgment calls to confirm at review (all reversible): `repr.tag_name`/`repr.call` -> class/function; `log.data.type` -> `Name.Class`; keeping `log.class`/`log.funcName` dimmed relative to the base.

## `theme.py` changes

- Import `build_syntax_styles` and merge its output into the `THEME` dict, alongside the still-hand-authored **non-syntax** entries: `log.level`/`log.name`/`log.name.sep`/`log.label`, all `datetime.*` and `timedelta.*`, `routine.sep`/`routine.call`/`routine.icon`, and `report.*`.
- Generated entries carry Rich ANSI names, so `THEME_ANSI_DARK = override_ansi_colors(THEME, **PALETTE_ANSI_DARK)` needs no change.
- Update the big inherited-defaults docstring to describe the Pygments-backed master, `STYLE_TOKENS`, and the ansi bridge.

## Enrich constant tidy-up

Repoint style-name constants that borrow the wrong namespace so they use the (now generated, consistent) names:

- [splatlog/rich/enrich/typ.py](splatlog/rich/enrich/typ.py): `_MODULE_STYLE = "inspect.class"` (a *module* rendered with a class style) and `_CLASS_STYLE = "repr.tag_name"`.
- [splatlog/rich/enrich/path.py](splatlog/rich/enrich/path.py): `_DIR_STYLE = "inspect.class"`, `_NAME_STYLE = "repr.tag_name"` -> `"repr.path"` / `"repr.filename"`.

`number.py`, `reporting.py`, `handler.py`, `routine.py`, `classifier.py`, `filter.py` already reference names that will now be master-backed — no changes needed.

## Docs & demonstration

- `dev/notes/2026-07-22.pygments-master-styles.ipynb`: show `routine.class`/`log.class`/`inspect.class`/`repr.tag_name` all resolving from `Name.Class`; show a custom subtype (`Name.Function.Method`) falling back to `Name.Function`; and (bonus) how swapping `SplatlogStyle` for a bundled Pygments style (e.g. `monokai`) retints everything.
- Add a doctest in `syntax_styles.py` asserting shared resolution + fallback (per the "show, don't tell" rule).
- Run `poe test` and `poe check`; watch the `to_style` doctests in [splatlog/rich/console.py](splatlog/rich/console.py) and the `theme` docstring examples for style-value drift.

## Out of scope (this pass)

- No public API to assign an external Pygments style/theme (kept internal; the bridge + token map make it a small follow-up).
- Not wiring the master into Rich's `Syntax`/traceback code-block highlighting beyond the existing `to_theme` `SyntaxTheme` refactor.
