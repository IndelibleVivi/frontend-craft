(() => {
  'use strict';
  const subjects = [
    { id:'tide', colors:['#dce4c3','#314c42'], en:['Tide','Where the tide leaves a line','Follow the edge between water and land.','An imaginary study of watermarks, quiet inlets and the small traces left when the sea moves away.'], zh:['潮汐','潮水退去，留下了一条线','沿着水与陆地之间的边缘走。','用流动的形体想象水痕、安静的海湾，以及潮水退去后留在岸边的细小痕迹。'] },
    { id:'canopy', colors:['#ebcb8a','#6b451f'], en:['Canopy','Beneath the branches, a different sky','Look up through overlapping leaves.','An imaginary study of layered leaves, interrupted sunlight and the shifting gaps between one branch and the next.'], zh:['树冠','在交叠的枝叶下，看见另一片天空','透过一层层叶片向上看。','用流动的形体想象层叠的树叶、断续的阳光，以及相邻枝条之间不断变化的空隙。'] },
    { id:'orbit', colors:['#d9dbee','#3c4173'], en:['Orbit','Small objects finding their own orbit','Notice what gathers around a center.','An imaginary study of circles, loose arrangements and ordinary objects that seem to gather around an invisible center.'], zh:['环绕','小小的物件，寻找各自的轨道','留意围绕着中心聚拢的事物。','用流动的形体想象圆形、松散的排列，以及仿佛围绕无形中心聚拢的日常物件。'] },
    { id:'moss', colors:['#bfd1a9','#384a31'], en:['Moss','A small forest on the north-facing wall','Find a landscape at the scale of a thumb.','An imaginary study of soft edges, damp corners and tiny landscapes growing where almost nobody thinks to look.'], zh:['苔藓','朝北的墙上，长出了一小片森林','在拇指大小的地方发现风景。','用流动的形体想象柔软的边缘、湿润的墙角，以及生长在人们很少留意之处的微小风景。'] },
    { id:'stone', colors:['#d6d1c8','#514b43'], en:['Stone','The slow stories held inside a stone','Read a surface shaped over time.','An imaginary study of grains, worn corners and lines that cross a stone without needing to explain where they began.'], zh:['石纹','一块石头里，藏着缓慢的故事','阅读被时间改变的表面。','用流动的形体想象颗粒、磨圆的棱角，以及横穿石面、无需说明来处的纹路。'] },
    { id:'dune', colors:['#eed5b8','#7c4b36'], en:['Dune','Every ridge remembers a passing wind','Trace a pattern that will not stay still.','An imaginary study of small ridges, drifting sand and the temporary patterns a moving wind leaves behind.'], zh:['沙丘','每一道沙脊，都记得经过的风','追踪无法静止的纹样。','用流动的形体想象细小的沙脊、流动的沙粒，以及风经过时留下的短暂纹样。'] },
    { id:'rain', colors:['#cadde5','#335462'], en:['Rain','Rain makes a map of every surface','Watch droplets choose their paths.','An imaginary study of window trails, puddle edges and the unexpected routes that falling water draws across a surface.'], zh:['雨迹','雨水为每一个表面，画出不同的地图','看水滴选择自己的路径。','用流动的形体想象窗上的水痕、水洼的边缘，以及落下的雨水在不同表面画出的意外路径。'] },
    { id:'pollen', colors:['#eee3a4','#686022'], en:['Pollen','A little dust from somewhere flowering','Follow a color carried through the air.','An imaginary study of fine yellow dust, flowering edges and small signs of a season arriving without an announcement.'], zh:['花粉','从某处盛开的花里，飘来一点微尘','追随空气携带的颜色。','用流动的形体想象淡黄的粉末、开花的边缘，以及一个季节悄悄到来时留下的细小信号。'] },
    { id:'current', colors:['#bcd8cf','#2c5b51'], en:['Current','The surface is still, the water is moving','Find direction inside a quiet surface.','An imaginary study of gentle eddies, floating leaves and the movements that become visible only when something drifts.'], zh:['水流','表面平静，水却一直在流动','在安静的表面里寻找方向。','用流动的形体想象缓慢的漩涡、漂浮的叶片，以及只有物件漂过时才显露的水流。'] },
    { id:'ember', colors:['#e8b9a2','#793c30'], en:['Ember','A warm trace after the flame has gone','Look for what lingers after a change.','An imaginary study of warm colors, fading edges and the traces that remain after something bright has passed.'], zh:['余烬','火焰离开后，仍然温暖的痕迹','寻找变化之后留下的东西。','用流动的形体想象暖色、渐淡的边缘，以及明亮的事物经过以后依然留下的痕迹。'] },
    { id:'frost', colors:['#e0e6df','#50645c'], en:['Frost','Overnight, the edges learned a new shape','Find geometry in a fleeting layer.','An imaginary study of pale branches, fine crystals and delicate geometries that disappear as the morning grows warmer.'], zh:['霜花','一夜之间，边缘长出了新的形状','在短暂的一层薄霜里寻找几何。','用流动的形体想象苍白的枝条、细小的结晶，以及在早晨回暖时逐渐消失的精巧形状。'] },
    { id:'afterglow', colors:['#ddcadb','#644660'], en:['Afterglow','The light that stays after the sun leaves','Watch the sky keep a little color.','An imaginary study of quiet horizons, lingering pinks and the gradual way a bright day becomes an ordinary evening.'], zh:['晚照','太阳离开之后，仍停留在天空的光','看天空保留最后一点颜色。','用流动的形体想象安静的地平线、迟迟未退的粉色，以及白昼缓缓变成普通傍晚的过程。'] }
  ];
  const copy={
    en:{skip:'Skip to the collection',edition:'EXPERIMENTS IN FORM / 001',series:'AN IMPOSSIBLE MATERIAL',title:['Liquid','matter.'],intro:'A little light.\nA surface that won’t sit still.',turnHint:'DRAG OR USE ARROW KEYS',reset:'Reset view ↺',collection:'Pick a fascination.',view:'Back to the sculpture ↑',choose:'Choose a sculpture',menuLabel:'All twelve subjects',settings:'Change the collection',setLabel:'Subjects',few:'3 subjects',many:'12 subjects',lengthLabel:'Words',short:'Short titles',long:'Long titles',presentationLabel:'Presentation',open:'Visible choices',compact:'Compact menu',tradeoff:'Visible choices invite comparison. The menu saves room, while keeping the selected subject in view. Reloading starts over.',footer:'Made of light, mathematics & a little curiosity.',boundary:'An original interactive artwork. No external assets. No stored data.',source:'Under the surface ↗',sourceNote:'One selected subject connects the sculpture, name and description. Authored shaders create the form and studio reflections; the material is an artistic interpretation, not a physical simulation.',selected:'NOW SHOWING',pause:'Pause motion Ⅱ',play:'Let it move ▷',canvas:'Sculpture. Drag with a mouse or use arrow keys to turn it.',unavailable:'The sculpture needs WebGL. This browser cannot render it; the collection’s names and descriptions remain available.'},
    zh:{skip:'跳到作品集合',edition:'形态实验 / 001',series:'一种不可能的材质',title:['流动的','物质。'],intro:'一点光。\n一个不肯静止的表面。',turnHint:'拖动或用方向键旋转',reset:'重置视角 ↺',collection:'选一种着迷。',view:'回到雕塑 ↑',choose:'选择一件雕塑',menuLabel:'全部十二个主题',settings:'调整作品集合',setLabel:'主题',few:'3 个主题',many:'12 个主题',lengthLabel:'文字',short:'短标题',long:'长标题',presentationLabel:'呈现方式',open:'展开选项',compact:'紧凑菜单',tradeoff:'展开选项便于比较；菜单节省空间，已选主题的说明依然可见。刷新页面会重新开始。',footer:'由光、数学，和一点好奇心构成。',boundary:'原创交互作品。无外部素材，不保存数据。',source:'看看表面之下 ↗',sourceNote:'同一个主题连接雕塑、名称与说明。原创 shader 绘制形态与摄影棚般的反光；材质属于艺术表达，不是物理模拟。',selected:'正在展出',pause:'暂停流动 Ⅱ',play:'让它流动 ▷',canvas:'交互雕塑。鼠标拖动或使用方向键旋转。',unavailable:'这件雕塑需要 WebGL；当前浏览器无法绘制。仍可查看集合中的名称和说明。'}
  };
  const state={language:'en',volume:'few',length:'short',presentation:'open',selectedId:'tide'};
  const $=id=>document.getElementById(id), words=()=>copy[state.language];
  const available=()=>subjects.slice(0,state.volume==='few'?3:12);
  const text=s=>s[state.language],title=s=>text(s)[state.length==='short'?0:1],description=s=>text(s)[state.length==='short'?2:3];
  const number=s=>String(subjects.indexOf(s)+1).padStart(2,'0');
  function write(element,value){element.replaceChildren(...value.split('\n').flatMap((line,i)=>i?[document.createElement('br'),document.createTextNode(line)]:[document.createTextNode(line)]));}
  function renderResult(){
    const subject=subjects.find(s=>s.id===state.selectedId);
    $('work-number').textContent=`${number(subject)} / ${String(available().length).padStart(2,'0')}`;
    $('work-name').textContent=title(subject);$('work-description').textContent=description(subject);
    $('compact-description').textContent=description(subject);
    $('selected-note').textContent=`${words().selected} ${number(subject)} · ${text(subject)[0]}`;
    window.sculpture.setSubject(subjects.indexOf(subject));
  }
  function renderOptions(){
    $('option-list').replaceChildren();
    for(const subject of available()){
      const label=document.createElement('label');label.className='choice';
      const swatch=document.createElement('span');swatch.className='material-swatch';swatch.style.setProperty('--swatch-a',subject.colors[0]);swatch.style.setProperty('--swatch-b',subject.colors[1]);swatch.setAttribute('aria-hidden','true');
      const input=document.createElement('input');input.type='radio';input.name='cover-subject';input.value=subject.id;input.checked=subject.id===state.selectedId;input.setAttribute('aria-label',`${number(subject)} · ${title(subject)}`);input.setAttribute('aria-describedby',`description-${subject.id}`);
      const content=document.createElement('span'),name=document.createElement('strong'),desc=document.createElement('span');
      name.textContent=`${number(subject)} · ${title(subject)}`;desc.className='description';desc.id=`description-${subject.id}`;desc.textContent=description(subject);content.append(name,desc);
      label.append(swatch,content,input);$('option-list').append(label);
    }
    $('subject').replaceChildren(...subjects.map(s=>{const option=document.createElement('option');option.value=s.id;option.textContent=`${number(s)} · ${title(s)}`;option.selected=s.id===state.selectedId;return option;}));
    const compact=state.volume==='many'&&state.presentation==='compact';
    $('visible-options').hidden=compact;$('compact-options').hidden=!compact;$('presentation').hidden=state.volume!=='many';
  }
  function renderMotion(){
    $('motion').textContent=window.sculpture.moving?words().pause:words().play;
    $('motion').setAttribute('aria-pressed',String(window.sculpture.moving));
    $('motion').disabled=!window.sculpture.available;$('reset-view').disabled=!window.sculpture.available;
    $('render-message').hidden=window.sculpture.available;$('render-message').textContent=words().unavailable;
  }
  function renderAll(){
    document.documentElement.lang=state.language==='en'?'en':'zh-CN';
    document.title=state.language==='en'?'Liquid Matter — Frontend Craft':'流动的物质 — Frontend Craft';
    document.querySelectorAll('[data-copy]').forEach(el=>{
      if(el.dataset.copy==='title'){const em=document.createElement('em');em.textContent=words().title[1];el.replaceChildren(document.createTextNode(words().title[0]),document.createElement('br'),em);}
      else write(el,words()[el.dataset.copy]);
    });
    $('language').textContent=state.language==='en'?'中文':'EN';$('language').lang=state.language==='en'?'zh-CN':'en';$('language').setAttribute('aria-label',state.language==='en'?'切换为中文':'Switch to English');
    $('sculpture').setAttribute('aria-label',words().canvas);
    renderOptions();renderResult();renderMotion();
  }
  document.addEventListener('change',event=>{
    const {name,value}=event.target;
    if(name==='cover-subject'||event.target.id==='subject'){state.selectedId=value;renderResult();}
    else if(['volume','length','presentation'].includes(name)){
      state[name]=value;if(!available().some(s=>s.id===state.selectedId))state.selectedId='tide';renderAll();
    }
  });
  $('language').addEventListener('click',()=>{state.language=state.language==='en'?'zh':'en';renderAll();});
  $('motion').addEventListener('click',()=>window.sculpture.toggle());$('reset-view').addEventListener('click',()=>window.sculpture.reset());
  document.addEventListener('sculpture-state',renderMotion);
  renderAll();
})();
