# Liquid Matter / 流动的物质

An original interactive sculpture: a folded loop with imagined iridescent
studio reflections, surrounded by typography and a small subject collection.
This is authored demonstration work. It does not establish autonomous FC output
quality, physical material accuracy, or owner aesthetic acceptance.

## Run and interact

From the repository root:

```sh
python3 -m http.server 4182 --bind 127.0.0.1
```

Open [the work](http://127.0.0.1:4182/examples/showcase/studies/choice-and-result/).
Drag horizontally on touch, drag with a mouse, or focus the sculpture and use
arrow keys to turn it. Vertical touch movement remains page scrolling. Pause
motion and reset the view with the labeled controls. Reduced motion starts
paused; explicit playback is available. Hidden pages and offscreen artwork
stop drawing. WebGL is required for the sculpture; unavailable graphics are
reported without disabling the text collection.

Choose a subject to change the shape parameters, optical color phase, title,
and description together. The collection contains twelve variations of one
sculpture system, not twelve separately modeled scenes. “Change the collection”
reveals three/twelve subjects, short/long labels, and visible/compact selection.
A smaller set keeps the current subject when available, otherwise selects Tide.
Language and presentation changes preserve selection; reload resets it.

There are no dependencies, remote assets, models, fonts, accounts, storage
writes, audio, or network calls beyond the local page files.

## Source and repeatable material

- [index.html](index.html): artwork, native collection controls, optional settings.
- [styles.css](styles.css): wide composition and a flowing narrow composition.
- [app.js](app.js): original bilingual records and selection/result ownership.
- [sculpture.js](sculpture.js): WebGL program, folded-loop distance field,
  surface normals, imaginary studio environment, optical color, camera turn,
  animation and visibility lifecycle.

The surface is defined by a modulated ring and rotated elliptical cross-section.
Ray marching finds its surface; finite differences estimate normals. A small
procedural environment supplies broad and narrow reflections. Color varies
with surface position and viewing angle; a grazing-angle term alters the edge.
These ingredients form one authored material treatment rather than a physical
metal or thin-film simulation. The shader contains no copied texture or model.
The [MDN WebGL tutorial](https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Tutorial/Adding_2D_content_to_a_WebGL_context)
was consulted for shader/program setup; the geometry and composition are original.

Preserve the relationship among folds, value range, broad reflection, edge
highlight, silhouette, and background when adapting the material. Merely
changing its colors does not establish another visual language. Adjust the
actual scene before adding explanatory controls. Keep a considered paused
pose. More elaborate geometry needs fresh surface and performance checks;
this finite renderer is not a general 3D engine.

## Verification scope

Chromium checks covered 1440 × 1000 and 390 × 844, English and Chinese,
selection/name/description agreement for twelve subjects, language and set
changes, long labels, compact selection, native radio keys, canvas arrow keys,
reload, and reduced motion. Actual captured pixels changed with animation and
keyboard turning, and stopped changing after pause. Offscreen drawing and resumption were observed; the hidden-document branch
was checked with a simulated visibility signal, not an OS tab switch. Mouse
dragging changed actual rendered pixels. Narrow long-content composition was
inspected after correction. Screenshots in
[the gallery guide](../../README.md#making-study-choice-and-result) show the
paused initial pose. Real touch hardware, screen readers, Safari/Firefox,
low-end GPU performance, and WebGL context recovery were not verified.

## 中文说明

这是一件可操作的原创雕塑：褶皱环状形体、想象中的虹彩反光、字体与作品集合共同组成画面。可拖动或用方向键旋转、暂停、重置；“调整作品集合”保留三/十二项、长短标题、展开/紧凑选择的实验。十二项属于同一形体系统的变化。减少动态时默认暂停；离屏与后台停止绘制。WebGL 不可用会明确提示。无外部依赖、素材、账号、存储或声音。

素材复用应保留褶皱、明暗、宽窄反光、轮廓和背景的关系，并在真实构图与静止状态下检查。这是艺术材质，不能声称物理精确；增加复杂形体需重新检查表面与性能。浏览器证据支持上述有限场景，不代表真实手机、所有浏览器、通用设计提升或用户已认可视觉效果。
