# Side A — design and implementation

Side A 的主要对象是音乐收藏，正在进行的活动是聆听。收藏占据中间的浏览空间；
正在播放的身份和控制固定在下方；接下来要听的内容按需在侧边展开。专辑页不是播放状态，
因此翻开另一张合辑不会替换当前声音。聆听视图暂时收起挑选环境，退出后回到原来的对象与位置。

这份记录描述当前产品的制作判断与实现，不把截图或执行者自评当作用户已经认可。

## 材料怎样组织画面

八张封面分别用夜景绘画裁切、柔和的几何叠置、斜向色带、地球摄影、重复曲线、花形、
线性排版与植物图形建立识别。浅色界面保持稳定，不随专辑替换整套背景；深绿播放器与
聆听空间让持续活动容易辨认。合辑编号用于连接缩略图和内页，不承担播放状态。

内页把封面与札记放在一个阅读区域，题名、真实署名、时长、主要动作与曲序放在另一侧。
队列出现时仍能看到正在浏览的合辑及其曲目，当前播放的封面在右侧和底部重复，说明它是
另一件对象。手机把队列改为可关闭的完整面板，内页札记排到曲目之后，避免丢内容或挤窄曲名。

DM Sans 用于 UI 和数字；中文使用系统字体。真实长中文合辑名、英文带括号曲名、
中英混合的个人歌单均参与浏览器检查。初版辅助文字过轻过小，实际渲染后提高了字号与对比；
手机封面收至 240px，使主要动作和第一首歌更早进入视口。

## 参考与转化

- 实际查看 [Doppler 官方队列图](https://brushedtype.co/assets/img/doppler-queue.png)
  与[功能页](https://brushedtype.co/doppler/features/)。借用的是“收藏可继续浏览、队列保留在相邻位置”
  的关系；没有复制截图、布局资产或其专辑取色功能。窄屏完整队列面板是本实现的适配。
- [Incompetech](https://incompetech.com/music/royalty-free/) 提供逐首真实作品与许可入口。
  选曲依据官方题名、作者与乐器信息；浏览器完整解码和实际播放已验证，未把这些检查写成主观试听评价。
- 两张历史图像的实际像素在合成前已查看。封面编排的源是
  [render-covers.mjs](../scripts/render-covers.mjs)，图像原件与各自条款见资产清单。

这些来源不支持“独创了队列”或“FC 普遍提高首稿质量”之类声明。它们支持具体材料和制作选择。

## 状态边界

`main.tsx` 只建立一个 audio 与 Player，生命周期高于浏览路由。`domain.ts` 负责队列出现项、
列表身份、循环与恢复规则；`player.ts` 负责实际媒体事件、请求代际与存储；`App.tsx` 负责
浏览对象、临时面板与交互。音源切换使旧 play promise 失效，不靠时钟模拟音频。

浏览路由保存在 hash/history，滚动位置按路由记录。队列用 occurrence ID；收藏用 track ID。
两个位置里同名的歌曲不会合并为一个队列项。UI 临时开关不存为播放事实。

本地存储拒绝写入时保留本页状态；原记录损坏、版本未知或含缺失对象时，先保留原始导出，
再提供明确的修复／重置动作。播放器恢复有效位置，但不会调用 play。

## 会推翻这个方向的结果

如果浏览 B 仍需要记住 A 才能理解当前状态，队列展开后曲目无法阅读，长内容被遮住，
或返回丢掉查询和位置，这个组织方式就没有成立。可运行和测试通过只覆盖可操作性；
画面是否值得反复打开、素材是否有吸引力，仍须在实际产品中判断。

## Portable listening state

JSON export and import use the same schema as the local save. `transfer.ts`
previews through the shared validator and prepares a merge with new occurrence
identities. `LibraryTransfer.tsx` owns the uncommitted file, mode and replacement
confirmation. `Player.importLibrary` is the sole commit owner: validate → derive
from the current snapshot → persist the complete candidate → publish state.
A failed write changes neither the library nor audio. Merge never reloads the
media element; replacement invalidates old playback requests and loads paused.

The preview places the incoming collection next to the current one, including
playlist names and queue counts. The user chooses a semantic operation rather
than resolving IDs. Repeated merges intentionally create another playlist copy;
Cancel retains unrelated edits and ongoing playback. Files are read locally,
size-limited to 2 MiB, and never uploaded. Existing damaged-state recovery stays
explicit. This does not coordinate concurrent browser tabs.

Audio preparation is a separate development operation. Builds and library JSON
never fetch recordings. The official source manifest and an explicit FFmpeg
command reconstruct ignored AAC files; generated output is checked against
each known duration before atomic placement.
