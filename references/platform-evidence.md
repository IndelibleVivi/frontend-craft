# Platform and host evidence

Read when the surface is not ordinary Web UI, the output is exported, or
needed runtime tools are missing. Design judgment can transfer across syntax;
runtime proof does not transfer automatically.

There are two independent questions: where the interface runs, and what the
executing host can inspect. Use available supported tools and current primary
platform guidance. Do not invent an API, install a stack without authority, or
replace an unavailable native check with a browser screenshot and call it done.

| Target | Appropriate evidence | Claim limit |
| --- | --- | --- |
| Web app / browser artifact | Exact route/build, browser render, live controls and states, layout/DOM, console, affected responsive and keyboard paths | Browser checks do not establish native device or owner acceptance |
| Native desktop / mobile | Exact app/build and target device or simulator; native semantics/accessibility tree, input/focus, window/device sizing and affected lifecycle using platform tools | A simulator does not prove every real-device behavior; this package does not ship a native automation adapter |
| Webview shell / installed PWA | Web content checks plus affected shell boundary: installed version/cache, navigation, file/clipboard bridge, or offline behavior when in scope | Browser-only success does not verify shell integration |
| Canvas / WebGL / procedural work | Real rendering plus logical object/state or hit-target evidence, accessible control path, meaningful interaction and temporal observation | DOM geometry alone cannot prove drawing or hit regions are correct |
| Exported graphic / document / media | Actual generated file opened in a suitable viewer at intended size; dimensions, fonts/assets and timing if relevant | Editor preview does not establish exported output |

## Work when capabilities are incomplete

Inspect available local code, rendering tools, project test setup, and supported
app/browser tools. Complete independent source and available checks. Identify
exactly what cannot be observed, why it matters, and the next concrete check.
Do not claim platform support from a renamed Web checklist.

This package provides a detailed Web QA method and a medium-aware validation
contract; it does not bundle a browser, native driver, device lab, font library,
asset generator, or persistent preference database. Tool absence changes the
evidence claim, not the user's requested outcome. Report a partial verification
when the missing layer remains material.
