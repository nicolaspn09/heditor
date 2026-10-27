# GSAP craft for heditor (plugins, seek safety, SVG preparation)

heditor compositions are rendered by HyperFrames: the timeline is paused and *seeked* to every frame, often by several
workers in parallel and out of order. Everything below is the official GSAP guidance (greensock/gsap-skills, MIT)
filtered through that constraint. When the two disagree, the seek rules win.

## Plugins available offline

Every GSAP plugin is free since 3.13 (same standard licence as the core). Setup downloads twelve of them to
`~/.heditor/assets/js/gsap/`, `rk.setup_assets` copies them into the cut, and `rk.page(..., plugins=(...))` loads and
registers the ones you ask for (`rk.gsap_plugin_tags(names)` gives the same tags for a hand-written page). Never load
plugins from a CDN in a composition: renders must work offline and with pinned versions.

| Plugin (`plugins=` name) | Use in a Reel | Seek-safe? |
|---|---|---|
| `SplitText` | per-character/word entrances, masked line reveals, kinetic titles | yes, if split once before the timeline is built (below) |
| `DrawSVG` | strokes that draw on the word: underlines, arrows, circles, icon outlines, signatures | yes |
| `MorphSVG` | icon → icon, shape → shape, logo assembly | yes (fix `shapeIndex`, see below) |
| `MotionPath` | an object riding a curve: a dot on a route, a cursor arc, a plane on a map | yes |
| `CustomEase`, `CustomBounce` | brand curves, a bounce with a set number of hits | yes |
| `CustomWiggle` | shakes and wobbles with a curve | only with `type: "easeOut"`, `"easeInOut"` or `"uniform"`; `"random"` calls `Math.random` |
| `TextPlugin` | type-on text replacement | yes |
| `Physics2D`, `PhysicsProps` | ballistic arcs (confetti, a thrown object) computed from time | yes (closed-form, no state) |
| `ScrambleText` | **avoid**: picks characters with `Math.random` on every update, so two workers draw different frames. Use the kit's deterministic `scramble(sel, text, t, dur)` | no |
| `EasePack` (`SlowMo`, `ExpoScaleEase`) | slow-motion middle, zooms that feel linear | yes; `RoughEase` is random, avoid |

ScrollTrigger, ScrollSmoother, Draggable, Inertia, Observer, Flip, `gsap.quickTo`, `gsap.matchMedia` and the React
helpers are interaction tools: they respond to scroll, pointer, resize or wall-clock time and have no place in a
rendered video. (They remain the right choice for web pages.)

## Determinism hazards inside GSAP itself

The core uses `Math.random` in a few convenient places. All of them break frame reproducibility:

- `gsap.utils.random()`, `gsap.utils.shuffle()`, string values like `x: "random(-100, 100)"`;
- `stagger: { from: "random" }` and `gsap.utils.distribute({ from: "random" })`;
- `CustomWiggle` with `type: "random"`, `RoughEase`, `ScrambleText`.

Use the seeded `rnd()` from the kit (seed in `keys["seed"]`) at build time instead: compute the values once, while the
timeline is built, and pass numbers (or a function of the index) to the tween. For a random stagger order, shuffle an
index array with `rnd()` and stagger with a function: `stagger: (i) => order[i] * 0.04`.

## Sequential seeks vs a single seek (preview and render disagree)

The render seeks frame after frame, in order, so it behaves like forward playback: when a tween is still running at
the moment a later `set`/tween on the same property fires, the earlier tween keeps rendering until it completes and
its end value wins. `heditor preview` seeks straight to each time, renders every child in start order and shows the
later `set`. The preview looks right and the MP4 does not (first avatar Reel: a 0.24 s yoyo blink on corner brackets
ended 0.08 s after the `set` that hid them, so the brackets stayed on screen until the end card).

- Never let two tweens/sets on the same property of the same element overlap: end the first before the second starts,
  and compute that from the timeline keys (`Math.min(a, b - duration - 0.05)`), because the cut moves when the speech
  is re-prepared.
- With the kit's `FT` helper (`immediateRender: false`), the *from* values are not applied before the tween starts:
  an element that must stay hidden until its word needs an explicit `set` (or CSS) before it.
- After the render, check the transitions on frames taken from the MP4 (`ffmpeg -ss <t> -i render.mp4 -frames:v 1`),
  not only on previews: the end of every section, the scene seams and the CTA.

## Rules worth applying from the official skills

- **Stacked `from()`/`fromTo()` on the same property:** set `immediateRender: false` on every later tween, or the first
  one is overwritten before it plays (the kit's `FT()` already does this). The first entrance of an element keeps the
  default so frame 0 is correct.
- **Transforms only for motion:** `x`, `y`, `xPercent`, `yPercent`, `scale`, `rotation`, `rotationX/Y`; never
  `left/top/width/height`. Percent transforms (`yPercent: 110`) are the clean way to slide text out of a mask.
- **Directional rotation:** `rotation: "-170_short"`, `"+=360_cw"`, `"_ccw"` pick the turn direction explicitly
  (dials, compasses, a logo spin that must end upright).
- **SVG pivots:** `svgOrigin: "250 100"` rotates or scales several SVG parts around one shared point in the SVG's own
  coordinates (gears, clock hands, an orbit). Never combine with `transformOrigin` on the same element.
- **CSS variables tween:** `"--hue": 180`, `"--fill": "62%"` drive gradients, masks and conic progress rings without
  layout work.
- **Grid staggers:** `stagger: { grid: [rows, cols], from: "center", amount: 0.6 }` (or `"edges"`, an index, or
  `[0.25, 0.75]`) for tiles, dot matrices and keyboards; `axis: "x"` for a sweep.
- **`gsap.utils` helpers at build time:** `mapRange` and `normalize` to turn spoken timestamps or data into positions,
  `interpolate("#1e3a8a", "#f5c66b", k)` for colour ramps, `snap` for grid-aligned layouts, `wrap` for cycling a list.
- **Avoid `clearProps`** in seekable timelines: it removes inline styles at completion, and seeking back does not
  restore them.
- **Labels and `defaults`:** `tl.addLabel("turn", 12.4)` and `gsap.timeline({ defaults: { ease: "power3.out" } })`
  keep long builds readable; the position parameter (`"<"`, `"<0.2"`, `"label+=0.3"`) replaces delays.

## SplitText in a render

0. Never split an element that is a flex container: the words become flex items and the spaces between them
   disappear. Put the text in an inner block span and split the span.

1. Split once, before building the timeline: `const s = SplitText.create("#title", { type: "words,chars" });`
2. Split only what you animate (`"chars"`, `"words"`, or `"words,chars"`). Splitting `"lines"` measures the layout,
   so it must run after the fonts load: build the timeline inside `document.fonts.ready.then(...)` and register it
   on `window.__timelines` only at the end of that callback (HyperFrames waits for the registration).
3. Never use `autoSplit` or `onSplit` re-splits: a re-split replaces the elements the timeline already targets.
4. Masked reveals: `mask: "lines"` (or `"words"`) wraps each unit in an `overflow: clip` element; animate
   `yPercent: 110 → 0` inside it.
5. To avoid kerning shifts when splitting characters: `font-kerning: none; text-rendering: optimizeSpeed;` on the
   element. Do not combine with `text-wrap: balance`. SplitText does not work on SVG `<text>`.
6. Accents and cedillas are single characters; check `Ç`, `Ã`, `É` in the preview at full size (combining marks in
   copied text become separate chars: normalise strings to NFC in Python first).

## DrawSVG and MorphSVG

- DrawSVG animates the *stroke*: the element needs `stroke` and `stroke-width`, and fills are untouched. `drawSVG`
  describes the visible segment: `fromTo(path, { drawSVG: "0% 0%" }, { drawSVG: "0% 100%" })` draws on,
  `"100% 100%"` wipes off forward, `"40% 60%"` → `"0% 100%"` grows from the middle.
- Prefer single-segment paths; a path with several `M` sub-paths draws all of them at once. Split complex artwork
  into one path per stroke and stagger them.
- MorphSVG morphs one path into one path. For icons made of several shapes (Lucide), merge them first:
  `svgkit.single_path(svg_text)` converts rect (with rx), circle, ellipse, line, polyline and polygon and joins
  everything into one `d` (a sub-path's leading relative `m` is rewritten so it stays where it was); the result is
  pixel-identical to the icon. Morph with the raw string: `morphSVG: {shape: d, type: "rotational"}`.
- MorphSVG converts shapes and adds points itself, but the start point matters: run once with
  `shapeIndex: "log"`, read the value in the console of a preview, then write the number in the build. Try
  `type: "rotational"` (and `curveMode: true` in 3.14) when a morph kinks halfway. `precompile: "log"` once for very
  complex paths. `MorphSVGPlugin.convertToPath("circle, rect, ellipse")` before morphing primitives.
- Rotating an SVG element (a gauge needle, a dial): GSAP applies `transformOrigin` relative to the element's own
  bounding box, so a needle spins around its tip or its centre instead of the pivot. Use `svgOrigin: "x y"` in the
  SVG's user coordinates (the pivot point of the dial), set once with `gsap.set` before the tweens.

## Prepare SVGs with `heditor svg` (SVGO)

Exported SVGs carry editor metadata, redundant groups and transforms, merged paths and long decimals. Clean them before
animating, with the mode that matches what the SVG will do:

```bash
heditor svg logo.svg                       # static: smallest file, ids kept for GSAP targets
heditor svg arrow.svg arrow.draw.svg draw  # DrawSVG: shapes and separate paths kept, 3 decimals
heditor svg icon.svg icon.morph.svg morph  # MorphSVG: shapes converted to <path>, paths kept separate
```

The command prints bytes and element counts before/after and renders the original and the result in the
HyperFrames Chrome: `ok` is false (exit code 1) when the pixels differ beyond a small tolerance, and
`<out>.check.png` shows original | optimised | difference side by side. In `build.py`,
`svgkit.inline(path, cls="logo", mode="draw", out_dir=work/"qa")` returns the cleaned markup and raises if the check
fails. Rounded rectangles (`rx`) are not converted to paths by SVGO; the morph report says so, and
`MorphSVGPlugin.convertToPath` handles them at runtime. Lucide icons are already clean; run them through `draw` only
to confirm they are single stroked paths.
