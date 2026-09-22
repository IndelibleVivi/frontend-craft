(() => {
  'use strict';

  const copy = {
    en: {
      skip: 'Skip to the example', examples: 'Examples', workflow: 'Note workflow ↗',
      authored: 'Authored synthetic examples of interface craft; not a quality benchmark or an autonomous agent run.',
      scoopMotto: 'Little scoops. Big feelings.', scoopStamp: 'HAPPINESS, SCOOPED DAILY',
      scoopEyebrow: 'A SMALL SCOOP OF SUMMER', scoopTitle: 'Life’s better\nwith sprinkles.',
      scoopArtNote: '100% good mood', scoopCaption: 'Made of pixels. Best enjoyed with a smile.',
      scoopMenu: 'THE GOOD STUFF', scoopChoose: 'Find your flavor.',
      scoopDescription: 'One golden waffle cone. One happy scoop.\nOne very important decision.',
      flavorLegend: 'Pick a flavor', berryName: 'Berry Sunday', berryNote: 'Strawberry & a little daydream',
      vanillaName: 'Vanilla Cloud', vanillaNote: 'Soft, sweet, wonderfully simple',
      mintName: 'Mint to Be', mintNote: 'Cool mint, tiny chocolate treasures',
      quantityLabel: 'How many cones?', quantityDown: 'One fewer cone', quantityUp: 'One more cone',
      yourScoop: 'YOUR HAPPY LITTLE TOTAL', total: 'Total in demonstration US dollars',
      scoopLocal: 'A make-believe shop. No orders or payments.', scoopFooter: 'A GOOD DAY STARTS WITH A LITTLE TREAT.',
      journalLabel: 'AN INDEPENDENT READING JOURNAL', journalIssue: 'VOL. 01 — THE EVERYDAY ISSUE',
      journalTagline: 'For the things you notice when you look away.', journalRoom: 'A little room to think ↙',
      inThisIssue: 'IN THIS ISSUE', essays: 'Essays',
      walkingTitle: 'The art of walking nowhere', walkingCategory: 'Attention · A short essay',
      windowTitle: 'A window left open', windowCategory: 'Home · A short essay',
      paperTitle: 'Things we keep on paper', paperCategory: 'Memory · A short essay',
      journalAside: 'No rush.\nThere is nowhere else\nyou need to be.', byline: 'Words from the Offscreen desk',
      essayEnd: 'A small thought to take with you.', readNext: 'Read the next essay',
      journalFooter: 'Less noise. More noticing.', fieldIntro: 'The space between\norder and surprise.',
      fieldStudio: 'AN INTERACTIVE LINE STUDY', fieldCaption: 'A quiet kind of infinite.',
      density: 'Line density', newVariation: 'New variation', pause: 'Pause motion', resume: 'Resume motion',
      fieldHint: 'Follow a line. See where it takes you.', fieldMotion: 'Move slowly. Change freely.',
      reducedMotion: 'Motion starts paused with your reduced-motion preference.',
      fieldTitle: 'Chromatic wave field',
      lineDescription: (density, variation) => `${density} colored lines form an undulating wave. Variation ${variation}.`,
      variation: number => `VARIATION ${String(number).padStart(2, '0')}`,
      essayIndex: index => `ESSAY ${String(index).padStart(2, '0')} / 03`,
      iceTitle: flavor => `${flavor} ice cream in a golden waffle cone, drawn in pixels`,
    },
    'zh-CN': {
      skip: '跳至当前示例', examples: '示例场景', workflow: '笔记工作流 ↗',
      authored: '这些是人工编写的虚构界面示例，并非质量基准，也不代表自主 Agent 的运行成果。',
      scoopMotto: '小小一勺，大大快乐。', scoopStamp: '每天，舀一勺快乐',
      scoopEyebrow: '舀一小勺夏天', scoopTitle: '生活有点甜，\n快乐多一点。',
      scoopArtNote: '百分百好心情', scoopCaption: '由像素制作，配上微笑享用。',
      scoopMenu: '甜蜜菜单', scoopChoose: '找到你的心头好。',
      scoopDescription: '一支金黄脆筒，一球快乐冰淇淋。\n只差一个甜蜜的决定。',
      flavorLegend: '选一种口味', berryName: '莓好星期天', berryNote: '草莓，和一点白日梦',
      vanillaName: '香草云朵', vanillaNote: '柔软香甜，简单就很好',
      mintName: '薄荷巧遇', mintNote: '清凉薄荷，藏着巧克力碎',
      quantityLabel: '想要几支？', quantityDown: '减少一支甜筒', quantityUp: '增加一支甜筒',
      yourScoop: '这一份小小快乐', total: '示例总价，单位美元',
      scoopLocal: '这是一家虚构小店，不会下单或付款。', scoopFooter: '美好的一天，从一点甜开始。',
      journalLabel: '一本独立阅读小刊', journalIssue: '第一卷 · 日常特辑',
      journalTagline: '把目光移开，才看见那些小事。', journalRoom: '留一点空白，慢慢想 ↙',
      inThisIssue: '本期目录', essays: '文章目录',
      walkingTitle: '漫无目的地走一走', walkingCategory: '留意 · 短篇随笔',
      windowTitle: '留一扇开着的窗', windowCategory: '居所 · 短篇随笔',
      paperTitle: '留在纸上的东西', paperCategory: '记忆 · 短篇随笔',
      journalAside: '不必匆忙。\n此刻，\n不必去往别处。', byline: '文字来自 Offscreen 编辑桌',
      essayEnd: '带走一个小小的念头。', readNext: '读下一篇', journalFooter: '少一点喧闹，多一点留意。',
      fieldIntro: '在秩序与惊喜\n之间，停留片刻。', fieldStudio: '一场可以触碰的线条实验',
      fieldCaption: '安静，也可以无穷无尽。', density: '线条密度', newVariation: '新的变化',
      pause: '暂停流动', resume: '继续流动', fieldHint: '沿着一条线，看看它会去哪里。',
      fieldMotion: '慢慢流动，自由变化。', reducedMotion: '遵循减少动态效果偏好，默认暂停流动。',
      fieldTitle: '彩色波浪线场',
      lineDescription: (density, variation) => `${density} 条彩色线条构成起伏的波浪，当前是第 ${variation} 个变化。`,
      variation: number => `变化 ${String(number).padStart(2, '0')}`,
      essayIndex: index => `随笔 ${String(index).padStart(2, '0')} / 03`,
      iceTitle: flavor => `金黄华夫甜筒中的${flavor}冰淇淋，由像素绘制`,
    },
  };

  const essays = {
    walking: {
      en: {
        heading: ['The art of', 'walking nowhere.'], category: 'ON ATTENTION',
        deck: 'What happens when the journey stops being a way to get somewhere, and becomes the thing itself?',
        paragraphs: [
          'Every Thursday, Mira took the long way home. Not the scenic route — there was no river, no celebrated row of trees — just three extra streets between the station and her front door. A repair shop. A low brick wall. A bakery that had already closed. She did not count the steps or call it a practice. She simply turned left where she usually turned right.',
          'At first, the detour seemed almost embarrassingly uneventful. Then she noticed the small changes. A green chair appeared outside the repair shop. Someone painted the wall the color of weak tea. In the bakery window, a paper moon moved a little farther from its paper sun. The streets had been having a quiet conversation without her.',
          'One evening, a sudden shower sent her under a narrow awning beside a stranger with a bag of leeks. They watched the rain bend the dust into little rivers. Neither checked the time. When the rain softened, they nodded and went in opposite directions, carrying the same unremarkable weather into different lives.',
          'Mira still arrived home. The kettle still needed filling. But the day no longer felt like something she had hurried through on the way to the next one. There had been a chair, a moon, a brief rain. Nothing had happened, and she had been there for all of it.',
        ],
      },
      'zh-CN': {
        heading: ['漫无目的地', '走一走。'], category: '关于留意',
        deck: '如果一段路不再只是抵达某处的方式，而成为这一天本身，会发生什么？',
        paragraphs: [
          '每个星期四，米拉都会绕远路回家。不是风景优美的那一条——没有河流，也没有知名的林荫道，只是在车站和家门之间多走三条街。一间修理铺，一堵矮砖墙，一家已经打烊的面包店。她不数步数，也不把这叫作某种练习。她只是走到平常右转的地方，向左转去。',
          '起初，这段绕路平淡得让人有点不好意思。后来，她开始注意到一些细小变化。修理铺外多了一把绿椅子。有人把矮墙刷成淡茶色。面包店的橱窗里，纸月亮离纸太阳又远了一点。那些街道一直在悄悄交谈，只是从前她没有听见。',
          '一天傍晚，骤雨把她赶到一小片雨棚下面，旁边站着一个拎着韭葱的陌生人。他们看雨水把灰尘推成弯弯曲曲的小河，谁都没有看时间。等雨势减弱，两个人互相点了点头，走向相反的方向，把同一场普通的天气带进各自的生活。',
          '米拉仍然回到了家，水壶也仍然需要灌满。但这一天不再像一段通往明天的匆忙过场。这里有过一把椅子，一轮月亮，一阵短雨。似乎什么也没发生，而她恰好没有错过。',
        ],
      },
    },
    window: {
      en: {
        heading: ['A window', 'left open.'], category: 'ON MAKING A HOME',
        deck: 'A room is never quite finished. Sometimes the thing it needs is a little more of the world outside.',
        paragraphs: [
          'The first thing Theo bought for the apartment was a small blue bowl. There was no table yet, so he placed it on the floor beside the window. For three days it held a key, two coins, and the folded receipt for itself. In the afternoons, a square of sunlight moved slowly past it, as if the room were learning where everything belonged.',
          'Furniture arrived. Books found shelves. The bowl moved to a table, then to a different table. Still, the apartment felt more arranged than lived in. Everything had been chosen, and every chosen thing seemed to be waiting for a reason to stay.',
          'On a warm morning, Theo opened the kitchen window and forgot to close it. From the courtyard came the tap of someone shaking a rug, then a laugh, then a piano trying the same six notes. A curtain lifted. The receipt fluttered out of the bowl. Nothing had been added to the room, but suddenly it had a place in a larger day.',
          'After that, he worried less about finishing the apartment. A book stayed open on a chair. The bowl collected a smooth stone from a walk. When the weather allowed, the window remained ajar. Home, he decided, might be less about getting every object right than leaving enough room for life to come in.',
        ],
      },
      'zh-CN': {
        heading: ['留一扇', '开着的窗。'], category: '关于居所',
        deck: '一间屋子从来不算真正布置完毕。有时，它需要的只是多一点窗外的世界。',
        paragraphs: [
          '西奥给新公寓买的第一件东西，是一只小蓝碗。那时还没有桌子，他把它放在窗边的地板上。连续三天，碗里装着一把钥匙、两枚硬币，还有买它时留下的折叠收据。午后，一方阳光缓缓从旁边移过，仿佛房间也在学习，每样东西应该待在哪里。',
          '家具送到了，书也上了架。小碗先搬到一张桌上，后来又换了一张。可这间公寓依旧更像被安排好的地方，而不是有人生活的地方。每样东西都经过挑选，每样被挑中的东西又似乎在等一个留下来的理由。',
          '一个暖和的早晨，西奥打开厨房的窗，随后忘了关上。院子里传来抖地毯的拍打声，接着是一声笑，再接着是一架反复练着六个音符的钢琴。窗帘扬了起来，收据从碗里飘落。房间里明明没有添置什么，却突然被安放进了更大的一天。',
          '从那以后，他不太着急把公寓布置完成了。一本翻开的书留在椅子上，小碗里多了一块散步捡来的光滑石头。天气允许时，窗总是半开着。他想，家或许不需要每件物品都恰到好处，只需要留出一点地方，让生活自己走进来。',
        ],
      },
    },
    paper: {
      en: {
        heading: ['Things we keep', 'on paper.'], category: 'ON SMALL MEMORIES',
        deck: 'A list, a margin, an ordinary scrap. Not everything we save was meant to become a keepsake.',
        paragraphs: [
          'Inside an old cookbook, Ada found a shopping list in her brother’s handwriting: lemons, rice, batteries, something green. It was not dated. There was no occasion she could attach to it, no remarkable dinner she remembered. The list had survived simply because nobody had thought to throw it away.',
          'She liked the last item best. Something green. The instruction left room for whatever looked good at the market, whatever was in season, whatever he could carry. She could hear him saying it. A little practical, a little distracted, already thinking about the next thing.',
          'Her phone held thousands of photographs, each one a deliberate attempt to remember. The list had tried to do nothing of the sort. Its ambition had been to make it through an afternoon. Yet here it was, preserving the shape of a familiar hand and the comfortable assumption that there would be dinner.',
          'Ada put it back between the same two pages. Later she wrote a list of her own on the back of an envelope: bread, pears, a new light bulb. She did not make it beautiful or add a date. Some things are kept because they matter. Others matter because, by chance, they were kept.',
        ],
      },
      'zh-CN': {
        heading: ['留在纸上的', '那些东西。'], category: '关于小小记忆',
        deck: '一张清单，一处页边，一片普通纸屑。并非所有留下来的东西，最初都打算成为纪念。',
        paragraphs: [
          '艾达在一本旧食谱里发现一张购物单，是哥哥的字迹：柠檬、大米、电池、买点绿色的东西。纸上没有日期，她也想不起与它有关的场合，更没有什么难忘的晚餐。这张清单能留下来，只是因为一直没有人想到要扔掉它。',
          '她最喜欢最后一项。买点绿色的东西。这句话留出了余地，可以是市场里看上去不错的、刚好当季的，或者他拎得动的任何东西。她几乎能听见他说话的声音：有点实际，有点心不在焉，思绪已经转向下一件事。',
          '她的手机里存着数千张照片，每一张都是有意留下的记忆。这张清单却没有那样的野心。它只想安稳地度过一个下午。可它就这样留了下来，保存着一只熟悉的手写字时的形状，也保存着一个令人安心的默认：晚上会有人一起吃饭。',
          '艾达把它放回原来的两页之间。后来，她在信封背面写了自己的清单：面包、梨、一个新灯泡。她没有特意写得漂亮，也没有添上日期。有些东西因为重要而被留下，另一些东西，则因为偶然留了下来，慢慢变得重要。',
        ],
      },
    },
  };

  const flavors = {
    berry: { price: 550, colors: ['#f19aa3', '#ffd5cd', '#c7657d', '#aa455b'] },
    vanilla: { price: 500, colors: ['#f4dda0', '#fff2ce', '#d3ae67', '#aa8554'] },
    mint: { price: 600, colors: ['#a0cdb3', '#d9f0cc', '#659b85', '#614e3f'] },
  };
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const state = {
    language: 'en', scene: 'scoop', flavor: 'berry', quantity: 1, essay: 'walking',
    field: { density: 56, variation: 1, phase: 0, playing: !reducedMotion.matches },
  };
  const $ = id => document.getElementById(id);
  const sceneButtons = [...document.querySelectorAll('[data-scene]')];
  const essayButtons = [...document.querySelectorAll('[data-essay]')];
  const essayKeys = Object.keys(essays);
  const svgNamespace = 'http://www.w3.org/2000/svg';
  let paths = [];
  let frameId = null;
  let lastFrame = null;
  let fieldParameters;

  function translatedText(element, text) {
    const pieces = text.split('\n');
    element.replaceChildren();
    pieces.forEach((piece, index) => {
      if (index) element.append(document.createElement('br'));
      element.append(document.createTextNode(piece));
    });
  }

  function renderShop() {
    const words = copy[state.language];
    const flavor = flavors[state.flavor];
    const name = words[`${state.flavor}Name`];
    ['--ice-main', '--ice-light', '--ice-shadow', '--ice-detail'].forEach((variable, index) => {
      $('scene-scoop').style.setProperty(variable, flavor.colors[index]);
    });
    $('display-flavor').textContent = name;
    $('ice-cream-title').textContent = words.iceTitle(name);
    $('quantity').value = state.quantity;
    $('quantity-down').disabled = state.quantity === 1;
    $('quantity-up').disabled = state.quantity === 6;
    $('order-description').textContent = `${state.quantity} × ${name}`;
    $('order-total').value = `$${(flavor.price * state.quantity / 100).toFixed(2)}`;
  }

  function renderEssay() {
    const essay = essays[state.essay][state.language];
    const heading = $('essay-title');
    const emphasis = document.createElement('em');
    emphasis.textContent = essay.heading[1];
    heading.replaceChildren(document.createTextNode(essay.heading[0]), document.createElement('br'), emphasis);
    $('essay-deck').textContent = essay.deck;
    $('essay-category').textContent = essay.category;
    $('essay-index').textContent = copy[state.language].essayIndex(essayKeys.indexOf(state.essay) + 1);
    $('essay-body').replaceChildren(...essay.paragraphs.map(text => {
      const paragraph = document.createElement('p');
      paragraph.textContent = text;
      return paragraph;
    }));
    essayButtons.forEach(button => {
      if (button.dataset.essay === state.essay) button.setAttribute('aria-current', 'true');
      else button.removeAttribute('aria-current');
    });
  }

  function renderFieldLabels() {
    const words = copy[state.language];
    $('density-value').value = state.field.density;
    $('variation-caption').textContent = words.variation(state.field.variation);
    $('motion-label').textContent = state.field.playing ? words.pause : words.resume;
    $('motion-icon').textContent = state.field.playing ? 'Ⅱ' : '▷';
    $('field-art-title').textContent = words.fieldTitle;
    $('field-art-description').textContent = words.lineDescription(state.field.density, state.field.variation);
    $('motion-note').textContent = reducedMotion.matches && !state.field.playing ? words.reducedMotion : words.fieldMotion;
  }

  function renderLanguage() {
    const words = copy[state.language];
    document.documentElement.lang = state.language;
    document.querySelectorAll('[data-i18n]').forEach(element => translatedText(element, words[element.dataset.i18n]));
    document.querySelectorAll('[data-i18n-aria]').forEach(element => element.setAttribute('aria-label', words[element.dataset.i18nAria]));
    $('language-toggle').textContent = state.language === 'en' ? '中文' : 'EN';
    $('language-toggle').setAttribute('aria-label', state.language === 'en' ? '切换为中文' : 'Switch to English');
    document.title = state.language === 'en' ? 'Frontend Craft — Three small worlds' : 'Frontend Craft — 三个小小世界';
    renderShop();
    renderEssay();
    renderFieldLabels();
  }

  function prepareField() {
    // A repeatable parameter space: each variation changes the wave's geometry and color.
    let seed = state.field.variation * 1021 + 713;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };
    fieldParameters = {
      tilt: (random() - .5) * .4,
      bend: .7 + random() * .65,
      twist: .8 + random() * 1.4,
      offset: random() * Math.PI * 2,
      amplitude: 82 + random() * 35,
    };
    const hueShift = state.field.variation === 1 ? 0 : Math.floor(random() * 220) - 60;
    const stops = [...document.querySelectorAll('#field-gradient stop')];
    const hues = [39, 9, 266, 220];
    stops.forEach((stop, index) => stop.setAttribute('stop-color', `hsl(${hues[index] + hueShift} 66% ${index === 0 ? 73 : 72}%)`));
  }

  function rebuildField() {
    paths = Array.from({ length: state.field.density }, () => {
      const path = document.createElementNS(svgNamespace, 'path');
      return path;
    });
    $('field-lines').replaceChildren(...paths);
    drawField();
    renderFieldLabels();
  }

  function drawField() {
    const { tilt, bend, twist, offset, amplitude } = fieldParameters;
    const phase = state.field.phase;
    paths.forEach((path, index) => {
      const v = index / (paths.length - 1);
      const layer = (v - .5) * 2;
      let d = '';
      for (let step = 0; step <= 148; step += 1) {
        const u = step / 148;
        const envelope = Math.sin(Math.PI * u);
        const angle = u * Math.PI * 2 * bend + offset + phase;
        const billow = Math.sin(angle + layer * twist) * amplitude * envelope;
        const fold = Math.cos(u * Math.PI * 2.6 + phase * .55 + layer * 1.6) * 38 * envelope;
        const width = 1090 - 82 * Math.cos(layer * 1.6);
        const x = 600 + (u - .5) * width + Math.sin(u * Math.PI * 2 + layer * 1.1) * 20 * envelope;
        const y = 282 + layer * (105 + 23 * Math.sin(angle)) + billow + fold + (u - .5) * tilt * 120;
        d += `${step === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      }
      path.setAttribute('d', d);
      path.setAttribute('opacity', (.48 + Math.sin(v * Math.PI) * .5).toFixed(2));
    });
  }

  function animateField(time) {
    if (lastFrame === null) lastFrame = time;
    const elapsed = time - lastFrame;
    if (elapsed >= 40) {
      state.field.phase += Math.min(elapsed, 80) * .00012;
      lastFrame = time;
      drawField();
    }
    frameId = window.requestAnimationFrame(animateField);
  }

  function syncAnimation() {
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
    lastFrame = null;
    if (state.scene === 'field' && state.field.playing && !document.hidden) {
      frameId = window.requestAnimationFrame(animateField);
    }
  }

  sceneButtons.forEach(button => button.addEventListener('click', () => {
    state.scene = button.dataset.scene;
    sceneButtons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.querySelectorAll('.scene').forEach(scene => { scene.hidden = scene.id !== `scene-${state.scene}`; });
    syncAnimation();
  }));
  $('language-toggle').addEventListener('click', () => {
    state.language = state.language === 'en' ? 'zh-CN' : 'en';
    renderLanguage();
  });
  document.querySelectorAll('input[name="flavor"]').forEach(input => input.addEventListener('change', () => {
    state.flavor = input.value;
    renderShop();
  }));
  $('quantity-down').addEventListener('click', () => { state.quantity -= 1; renderShop(); });
  $('quantity-up').addEventListener('click', () => { state.quantity += 1; renderShop(); });
  essayButtons.forEach(button => button.addEventListener('click', () => {
    state.essay = button.dataset.essay;
    renderEssay();
  }));
  $('next-essay').addEventListener('click', () => {
    state.essay = essayKeys[(essayKeys.indexOf(state.essay) + 1) % essayKeys.length];
    renderEssay();
    $('essay-title').setAttribute('tabindex', '-1');
    $('essay-title').focus({ preventScroll: true });
    $('essay-title').scrollIntoView({ block: 'start', behavior: 'instant' });
  });
  $('density').addEventListener('input', event => {
    state.field.density = Number(event.target.value);
    rebuildField();
  });
  $('new-variation').addEventListener('click', () => {
    state.field.variation += 1;
    prepareField();
    drawField();
    renderFieldLabels();
  });
  $('toggle-motion').addEventListener('click', () => {
    state.field.playing = !state.field.playing;
    renderFieldLabels();
    syncAnimation();
  });
  reducedMotion.addEventListener('change', () => {
    if (reducedMotion.matches) state.field.playing = false;
    renderFieldLabels();
    syncAnimation();
  });
  document.addEventListener('visibilitychange', syncAnimation);

  prepareField();
  rebuildField();
  renderLanguage();
})();
