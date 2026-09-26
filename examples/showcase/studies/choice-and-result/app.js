(() => {
  'use strict';
  // Authored synthetic records. IDs stay stable across language and copy length.
  const subjects = [
    { id:'tide', colors:['#dce4c3','#314c42'], en:['Tide','Where the tide leaves a line','Follow the edge between water and land.','A field guide to watermarks, quiet inlets and the small traces left when the sea moves away.'], zh:['潮汐','潮水退去，留下了一条线','沿着水与陆地之间的边缘走。','一份虚构的观察手册，记录水痕、安静的海湾，以及潮水退去后留在岸边的细小痕迹。'] },
    { id:'canopy', colors:['#ebcb8a','#6b451f'], en:['Canopy','Beneath the branches, a different sky','Look up through overlapping leaves.','A field guide to layered leaves, interrupted sunlight and the shifting gaps between one branch and the next.'], zh:['树冠','在交叠的枝叶下，看见另一片天空','透过一层层叶片向上看。','一份虚构的观察手册，记录层叠的树叶、断续的阳光，以及相邻枝条之间不断变化的空隙。'] },
    { id:'orbit', colors:['#d9dbee','#3c4173'], en:['Orbit','Small objects finding their own orbit','Notice what gathers around a center.','A field guide to circles, loose arrangements and ordinary objects that seem to gather around an invisible center.'], zh:['环绕','小小的物件，寻找各自的轨道','留意围绕着中心聚拢的事物。','一份虚构的观察手册，记录圆形、松散的排列，以及仿佛围绕无形中心聚拢的日常物件。'] },
    { id:'moss', colors:['#bfd1a9','#384a31'], en:['Moss','A small forest on the north-facing wall','Find a landscape at the scale of a thumb.','A field guide to soft edges, damp corners and tiny landscapes growing where almost nobody thinks to look.'], zh:['苔藓','朝北的墙上，长出了一小片森林','在拇指大小的地方发现风景。','一份虚构的观察手册，记录柔软的边缘、湿润的墙角，以及生长在人们很少留意之处的微小风景。'] },
    { id:'stone', colors:['#d6d1c8','#514b43'], en:['Stone','The slow stories held inside a stone','Read a surface shaped over time.','A field guide to grains, worn corners and lines that cross a stone without needing to explain where they began.'], zh:['石纹','一块石头里，藏着缓慢的故事','阅读被时间改变的表面。','一份虚构的观察手册，记录颗粒、磨圆的棱角，以及横穿石面、无需说明来处的纹路。'] },
    { id:'dune', colors:['#eed5b8','#7c4b36'], en:['Dune','Every ridge remembers a passing wind','Trace a pattern that will not stay still.','A field guide to small ridges, drifting sand and the temporary patterns a moving wind leaves behind.'], zh:['沙丘','每一道沙脊，都记得经过的风','追踪无法静止的纹样。','一份虚构的观察手册，记录细小的沙脊、流动的沙粒，以及风经过时留下的短暂纹样。'] },
    { id:'rain', colors:['#cadde5','#335462'], en:['Rain','Rain makes a map of every surface','Watch droplets choose their paths.','A field guide to window trails, puddle edges and the unexpected routes that falling water draws across a surface.'], zh:['雨迹','雨水为每一个表面，画出不同的地图','看水滴选择自己的路径。','一份虚构的观察手册，记录窗上的水痕、水洼的边缘，以及落下的雨水在不同表面画出的意外路径。'] },
    { id:'pollen', colors:['#eee3a4','#686022'], en:['Pollen','A little dust from somewhere flowering','Follow a color carried through the air.','A field guide to fine yellow dust, flowering edges and small signs of a season arriving without an announcement.'], zh:['花粉','从某处盛开的花里，飘来一点微尘','追随空气携带的颜色。','一份虚构的观察手册，记录淡黄的粉末、开花的边缘，以及一个季节悄悄到来时留下的细小信号。'] },
    { id:'current', colors:['#bcd8cf','#2c5b51'], en:['Current','The surface is still, the water is moving','Find direction inside a quiet surface.','A field guide to gentle eddies, floating leaves and the movements that become visible only when something drifts.'], zh:['水流','表面平静，水却一直在流动','在安静的表面里寻找方向。','一份虚构的观察手册，记录缓慢的漩涡、漂浮的叶片，以及只有物件漂过时才显露的水流。'] },
    { id:'ember', colors:['#e8b9a2','#793c30'], en:['Ember','A warm trace after the flame has gone','Look for what lingers after a change.','A field guide to warm colors, fading edges and the traces that remain after something bright has passed.'], zh:['余烬','火焰离开后，仍然温暖的痕迹','寻找变化之后留下的东西。','一份虚构的观察手册，记录暖色、渐淡的边缘，以及明亮的事物经过以后依然留下的痕迹。'] },
    { id:'frost', colors:['#e0e6df','#50645c'], en:['Frost','Overnight, the edges learned a new shape','Find geometry in a fleeting layer.','A field guide to pale branches, fine crystals and delicate geometries that disappear as the morning grows warmer.'], zh:['霜花','一夜之间，边缘长出了新的形状','在短暂的一层薄霜里寻找几何。','一份虚构的观察手册，记录苍白的枝条、细小的结晶，以及在早晨回暖时逐渐消失的精巧形状。'] },
    { id:'afterglow', colors:['#ddcadb','#644660'], en:['Afterglow','The light that stays after the sun leaves','Watch the sky keep a little color.','A field guide to quiet horizons, lingering pinks and the gradual way a bright day becomes an ordinary evening.'], zh:['晚照','太阳离开之后，仍停留在天空的光','看天空保留最后一点颜色。','一份虚构的观察手册，记录安静的地平线、迟迟未退的粉色，以及白昼缓缓变成普通傍晚的过程。'] }
  ];
  const copy = {
    en: {
      skip:'Skip to the experiment',series:'MAKING STUDY / 01',eyebrow:'CHOICE → RESULT',title:'Keep the choice\nin the picture.',intro:'A few options can tell a complete story. Add more words or more choices, and that relationship needs another shape.',start:'Try the relationship ↓',experimentTitle:'One cover. A changing set of choices.',synthetic:'AUTHORED · SYNTHETIC',setLabel:'Change the set',few:'3 options',many:'12 options',lengthLabel:'Stretch the words',short:'Short copy',long:'Long copy',choose:'Choose a cover subject',presentationLabel:'Show the set as',open:'Visible options',compact:'Compact menu',menuLabel:'Cover subject — all 12 options',compactNote:'The menu saves space; descriptions are no longer visible together. The selected subject stays in the result.',resultLabel:'THE RESULT · LIVE',coverSeries:'A SMALL ATLAS',coverKicker:'NOTICING THE EVERYDAY',coverFooter:'An imaginary field guide',resultNote:'Title, drawing and description come from the same selected record.',readingEyebrow:'TAKE THE RELATIONSHIP, NOT THE SKIN',readingTitle:'Keep identity close.\nLet the form change.',readingIntro:'A useful choice explains both “which one?” and “what changed?” The control alone cannot do all of that work.',fitTitle:'When it earns the space',fit:'A small, mutually exclusive set with useful differences. Visible labels and descriptions support comparison; a nearby result makes the consequence inspectable.',breakTitle:'Where it starts to strain',break:'Long descriptions increase the distance between choices. A large set demands scrolling. On a phone, a result after the full list can disappear from the working position.',costTitle:'What the alternative costs',cost:'A menu keeps a long set compact, but hides alternatives until opened and weakens side-by-side comparison. If people need several choices, use a multi-select pattern; if they need an exact quantity, use a numeric control.',sourceTitle:'Download the source & follow the mechanism',sourceIntro:'One selected ID drives every output. Changing language translates that same record; it does not choose another one. Short and long copy are authored variants. Reloading resets this study. Returning to three options keeps the subject if available, otherwise selects Tide.',htmlNote:'Semantic radio groups, a native menu and the result region.',cssNote:'A shared workbench on wide screens; a compact live result above choices on phones.',jsNote:'Synthetic bilingual records, selected ID and a single result renderer.',provenance:'Adapted relationship from',provenanceEnd:': visible choices and an immediate, named result.',boundary:'Synthetic teaching material, not a recording of a real product workflow or a design-quality benchmark.',shortHint:'Pick a subject below. Then add words or options and watch what changes.',longHint:'The record stays the same. Its label and description now need more room.',manyHint:'The set grew. Compare the visible list with a compact menu below.',footFew:'Three mutually exclusive subjects. Select another to change the same cover immediately.',footMany:'Twelve mutually exclusive subjects. Scroll the list, then try the compact menu to compare the cost.',footCompact:'All twelve records are available. Opening the menu adds one interaction; the selected description remains visible.',selected:'Selected',obsFewTitle:'Three options can share one glance.',obsFew:'The options expose their differences before you choose. A matching name and number connect the active row to the cover; the drawing and description respond immediately.',obsLongTitle:'More words change the geometry.',obsLong:'The same three records need taller rows. Labels wrap instead of being cut off, but comparison now takes more space. On a phone, the compact live cover stays above the choices; it also occupies part of the viewport.',obsManyTitle:'Visibility has a space cost.',obsMany:'Twelve open choices push some alternatives below the fold. The nearby result preserves identity, but cannot make the full set easy to compare. Try “Compact menu” to trade simultaneous descriptions for a shorter control.',obsCompactTitle:'Compact is a trade, not a verdict.',obsCompact:'The menu brings the result and control closer. It also hides the other descriptions: you must select each subject to inspect it. Keep a visible set when those differences matter more than the space saved.'
    },
    zh: {
      skip:'跳到试验区',series:'制作研究 / 01',eyebrow:'选择 → 结果',title:'让选择，\n留在画面里。',intro:'少量选项可以讲清一个完整关系。文字变长，选项变多，这个关系就需要另一种表达。',start:'动手试试这个关系 ↓',experimentTitle:'同一张封面，变化的选项。',synthetic:'人工编写 · 虚构材料',setLabel:'改变选项数量',few:'3 个选项',many:'12 个选项',lengthLabel:'拉长文字',short:'短文案',long:'长文案',choose:'选择一个封面主题',presentationLabel:'选项的呈现方式',open:'全部可见',compact:'紧凑菜单',menuLabel:'封面主题——共 12 个选项',compactNote:'菜单节省了空间，但各项说明不再同时可见。已选主题仍然留在结果里。',resultLabel:'结果 · 即时更新',coverSeries:'一本小小的图集',coverKicker:'观察日常',coverFooter:'一本虚构的观察手册',resultNote:'标题、图形和说明，来自同一条选中记录。',readingEyebrow:'借用关系，而非外观',readingTitle:'让身份靠近。\n让形式改变。',readingIntro:'一次清楚的选择，同时回答“选中了哪个”和“什么发生了变化”。单靠控件，做不到全部。',fitTitle:'什么时候值得占用空间',fit:'选项少、互斥，而且差异值得比较时。把名称和说明直接展开，可以在选择前比较；附近的结果，让变化能够被检查。',breakTitle:'什么时候开始吃力',break:'说明变长，会拉开选项之间的距离。数量增多，需要来回滚动。在手机上，如果结果排在整个长列表之后，它就可能离开当前操作的位置。',costTitle:'替代表达也有代价',cost:'菜单让长列表更紧凑，但打开前看不到其他选项，也削弱了同时比较。如果需要选择多项，应采用多选控件；如果需要精确数量，应使用数字输入。',sourceTitle:'下载源码，追踪这个机制',sourceIntro:'所有结果由同一个选中 ID 驱动。切换语言只翻译这条记录，不会改选其他记录。长短文案都为人工编写的版本；刷新会重置。回到三个选项时，保留其中已有的主题，否则选中“潮汐”。',htmlNote:'语义化单选组、原生菜单与结果区域。',cssNote:'宽屏并排；手机上将精简即时结果保留在选项上方。',jsNote:'虚构中英记录、选中 ID 与统一的结果渲染函数。',provenance:'机制来源：',provenanceEnd:'，可见的选项与即时、有名称的结果。',boundary:'虚构的制作教学材料，不是真实产品工作流的录像，也不是设计质量基准。',shortHint:'先选择一个主题，再增加文字或选项，观察关系怎样变化。',longHint:'记录没有改变；它的名称和说明现在需要更多空间。',manyHint:'选项变多了。比较下方的可见列表与紧凑菜单。',footFew:'三个互斥的主题。选择另一项，同一张封面立即变化。',footMany:'十二个互斥的主题。滚动浏览，再试试紧凑菜单，比较两种表达的代价。',footCompact:'十二条记录都可选择。打开菜单多了一步；已选项的完整说明仍然可见。',selected:'已选择',obsFewTitle:'三个选项，可以放进同一眼里。',obsFew:'每项差异在选择前就可见。相同的名称和编号连接着选中行与封面；图形和说明也会立即响应。',obsLongTitle:'文字变长，空间关系也会改变。',obsLong:'同样的三条记录，需要更高的行。名称完整换行，比较因此占用更多空间。手机上的精简封面会留在选项上方；这也会占去一部分视口。',obsManyTitle:'保持可见，需要付出空间。',obsMany:'十二个展开的选项，把部分候选项推到了首屏之外。附近的结果保留了身份联系，却不能让整组选项更容易比较。试试“紧凑菜单”，用同时可见的说明换取更短的控件。',obsCompactTitle:'紧凑是一种取舍，不是结论。',obsCompact:'菜单拉近了控件与结果，但也藏起了其他说明：需要逐个选择，才能检查各主题。当这些差异比省下的空间更重要时，保持选项可见更合适。'
    }
  };
  const state = {language:'en',volume:'few',length:'short',presentation:'open',selectedId:'tide'};
  const $ = id => document.getElementById(id);
  const words = () => copy[state.language];
  const available = () => subjects.slice(0,state.volume === 'few' ? 3 : 12);
  const text = subject => subject[state.language];
  const title = subject => text(subject)[state.length === 'short' ? 0 : 1];
  const description = subject => text(subject)[state.length === 'short' ? 2 : 3];
  const number = subject => String(subjects.indexOf(subject)+1).padStart(2,'0');
  function write(element,value) {
    element.replaceChildren(...value.split('\n').flatMap((line,index) => index ? [document.createElement('br'),document.createTextNode(line)] : [document.createTextNode(line)]));
  }
  // An original code-drawn cover motif, not a quantitative chart.
  function drawing(index) {
    const type = index % 3;
    let paths = '';
    if (type === 0) {
      for(let line=0;line<12;line++) {
        const y=20+line*12;
        paths += `<path d="M26 ${y} C88 ${y-48-index}, 134 ${y+58}, 190 ${y+4} S276 ${y-36},334 ${y+3}"/>`;
      }
    } else if (type === 1) {
      for(let leaf=0;leaf<11;leaf++) {
        const x=57+leaf*24;
        paths += `<path d="M180 180 Q${x-74} ${25+index},${x} 18 Q${x+30} 118,180 180Z"/>`;
      }
    } else {
      for(let ring=0;ring<10;ring++) {
        paths += `<ellipse cx="180" cy="95" rx="${42+ring*10}" ry="${23+ring*6}" transform="rotate(${index*5+ring*9} 180 95)"/>`;
      }
    }
    return `<svg viewBox="0 0 360 200" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="currentColor" stroke-width="1.15">${paths}</g></svg>`;
  }
  function renderResult() {
    const subject=subjects.find(item => item.id === state.selectedId);
    $('cover').style.setProperty('--cover-bg',subject.colors[0]);
    $('cover').style.setProperty('--cover-ink',subject.colors[1]);
    $('cover-id').textContent=number(subject);
    $('cover-title').textContent=title(subject);
    $('cover-deck').textContent=description(subject);
    $('cover-art').innerHTML=drawing(subjects.indexOf(subject));
    $('result-status').textContent=`${words().selected} ${number(subject)} · ${title(subject)}`;
    // Long mobile results may grow over the focused row after a native arrow-key change.
    // Keep the complete current label below the sticky result at that working position.
    const active = document.activeElement;
    if (active.name === 'cover-subject' && window.matchMedia('(max-width: 760px)').matches) {
      const row = active.closest('label').getBoundingClientRect();
      const resultBottom = document.querySelector('.result').getBoundingClientRect().bottom;
      if (row.top < resultBottom + 12) window.scrollBy(0, row.top - resultBottom - 12);
    }
  }
  function renderOptions() {
    const list=$('option-list');
    list.replaceChildren();
    for(const subject of available()) {
      const label=document.createElement('label');
      label.className='choice';
      const input=document.createElement('input');
      input.type='radio';input.name='cover-subject';input.value=subject.id;
      input.checked=subject.id===state.selectedId;
      const content=document.createElement('span');
      const name=document.createElement('strong');name.textContent=title(subject);
      const desc=document.createElement('span');desc.className='description';desc.textContent=description(subject);
      content.append(name,desc);
      const icon=document.createElement('span');icon.className='choice-icon';icon.style.color=subject.colors[1];icon.textContent=number(subject);icon.setAttribute('aria-hidden','true');
      label.append(input,content,icon);list.append(label);
    }
    $('subject').replaceChildren(...subjects.map(subject => {
      const option=document.createElement('option');option.value=subject.id;option.textContent=`${number(subject)} · ${title(subject)}`;option.selected=subject.id===state.selectedId;return option;
    }));
    const compact=state.volume==='many'&&state.presentation==='compact';
    $('visible-options').hidden=compact;
    $('compact-options').hidden=!compact;
    $('presentation').hidden=state.volume!=='many';
    $('count').textContent=state.volume==='few'?'03':'12';
  }
  function renderExplanation() {
    const w=words();
    const compact=state.volume==='many'&&state.presentation==='compact';
    const key=compact?'Compact':state.volume==='many'?'Many':state.length==='long'?'Long':'Few';
    $('observation-title').textContent=w[`obs${key}Title`];
    $('observation-copy').textContent=w[`obs${key}`];
    $('condition-note').textContent=state.volume==='many'?w.manyHint:state.length==='long'?w.longHint:w.shortHint;
    $('selection-foot').textContent=compact?w.footCompact:state.volume==='many'?w.footMany:w.footFew;
  }
  function renderAll() {
    document.documentElement.lang=state.language==='en'?'en':'zh-CN';
    document.title=state.language==='en'?'Choice & result — Frontend Craft making study':'选择与结果 — Frontend Craft 制作研究';
    document.querySelectorAll('[data-copy]').forEach(element => write(element,words()[element.dataset.copy]));
    $('language').textContent=state.language==='en'?'中文':'EN';
    $('language').lang=state.language==='en'?'zh-CN':'en';
    $('language').setAttribute('aria-label',state.language==='en'?'切换为中文':'Switch to English');
    renderOptions();renderResult();renderExplanation();
  }
  document.addEventListener('change',event => {
    const {name,value}=event.target;
    if(name==='cover-subject'||event.target.id==='subject') {
      state.selectedId=value;renderResult();
    } else if(['volume','length','presentation'].includes(name)) {
      state[name]=value;
      if(!available().some(subject=>subject.id===state.selectedId))state.selectedId='tide';
      renderAll();
    }
  });
  $('language').addEventListener('click',()=>{state.language=state.language==='en'?'zh':'en';renderAll();});
  renderAll();
})();
