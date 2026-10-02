/* Original WebGL sculpture and studio lighting. No libraries or remote assets. */
(() => {
  'use strict';
  const canvas=document.getElementById('sculpture');
  const gl=canvas.getContext('webgl',{alpha:true,antialias:false,premultipliedAlpha:false});
  const vertex=`attribute vec2 position; void main(){gl_Position=vec4(position,0.,1.);}`;
  const fragment=`
    precision highp float;
    uniform vec2 resolution;
    uniform float time, subject;
    uniform vec2 turn;
    mat2 rotation(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
    vec3 localPoint(vec3 p){
      p.xz=rotation(.32+turn.x+time*.12)*p.xz;
      p.yz=rotation(-.43+turn.y)*p.yz;
      p.xy=rotation(-.38+sin(time*.19)*.08)*p.xy;
      return p;
    }
    float surface(vec3 world){
      vec3 p=localPoint(world);
      float angle=atan(p.y,p.x);
      float family=mod(subject,3.);
      float lobes=family<.5?3.:family<1.5?5.:2.;
      float radius=1.12+.14*cos(angle*lobes+subject*.8);
      float twist=.29*sin(angle*lobes+time*.22+subject);
      vec2 tube=vec2(length(p.xy)-radius,p.z-twist);
      tube=rotation(angle*(family<1.5?1.5:2.)+time*.16)*tube;
      tube.y*=1.55;
      float thickness=.38+.055*sin(angle*lobes-time*.3);
      return (length(tube)-thickness)*.54;
    }
    vec3 normalAt(vec3 p){
      vec2 e=vec2(.002,0.);
      return normalize(vec3(surface(p+e.xyy)-surface(p-e.xyy),surface(p+e.yxy)-surface(p-e.yxy),surface(p+e.yyx)-surface(p-e.yyx)));
    }
    vec3 studio(vec3 r){
      vec3 sky=mix(vec3(.08,.035,.13),vec3(.7,.59,.76),smoothstep(-.7,.65,r.y));
      float strip=pow(max(0.,dot(r,normalize(vec3(-.45,.8,.35)))),18.);
      float edge=pow(max(0.,dot(r,normalize(vec3(.85,.25,-.4)))),32.);
      float silk=pow(max(0.,dot(r,normalize(vec3(-.65,-.4,.5)))),7.);
      return sky+vec3(1.,.91,.87)*strip*3.2+vec3(.71,.88,1.)*edge*2.7+vec3(.71,.25,.54)*silk*.55;
    }
    void main(){
      vec2 uv=(gl_FragCoord.xy-.5*resolution)/resolution.y;
      vec3 origin=vec3(0.,0.,5.7);
      vec3 ray=normalize(vec3(uv*3.9,-5.7));
      // The bounding sphere skips expensive marching outside the actual work.
      float b=dot(origin,ray),c=dot(origin,origin)-4.4;
      float discriminant=b*b-c;
      if(discriminant<0.){gl_FragColor=vec4(0.);return;}
      float distance=max(0.,-b-sqrt(discriminant));
      float end=-b+sqrt(discriminant);
      vec3 point=origin+ray*distance;
      bool hit=false;
      for(int i=0;i<160;i++){
        point=origin+ray*distance;
        float step=surface(point);
        if(step<.0015){hit=true;break;}
        distance+=step;
        if(distance>end)break;
      }
      if(!hit){gl_FragColor=vec4(0.);return;}
      vec3 n=normalAt(point),view=-ray,reflection=reflect(ray,n);
      float fresnel=pow(1.-max(0.,dot(n,view)),3.);
      vec3 object=localPoint(point);
      float phase=subject*.49+object.z*1.4+object.y*.6+dot(n,view)*3.;
      vec3 film=.55+.45*cos(vec3(0.,2.05,4.1)+phase);
      vec3 tint=mix(vec3(.79,.37,.65),film,.68);
      float diffuse=.32+.68*max(0.,dot(n,normalize(vec3(-.5,.85,1.))));
      vec3 reflected=studio(reflection);
      vec3 color=tint*diffuse*.48+reflected*mix(tint,vec3(1.),.38+fresnel*.55)*.82;
      // Broad reflections remain legible through the folded interior.
      float cavity=clamp(length(object.xy)*.7,.4,1.);
      color*=cavity;
      color+=vec3(.42,.12,.33)*fresnel*.2;
      color=color/(1.+color*.36);
      color=pow(color,vec3(.4545));
      gl_FragColor=vec4(color,1.);
    }`;
  let program;
  function setup(){
    if(!gl)return false;
    const compile=(type,source)=>{
      const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      return shader;
    };
    program=gl.createProgram();
    gl.attachShader(program,compile(gl.VERTEX_SHADER,vertex));
    gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    return true;
  }
  let available=false;
  try{available=setup();}catch(error){console.error('Sculpture renderer:',error.message);}
  const uniforms=available?Object.fromEntries(['resolution','time','subject','turn'].map(name=>[name,gl.getUniformLocation(program,name)])):{};
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let moving=!reduced.matches, visible=true, frame=0, elapsed=2.4, previous=0, subject=0, turn=[0,0], drag=null;
  function draw(now){
    frame=0;
    if(!available||document.hidden||!visible)return;
    if(moving&&previous)elapsed+=Math.min((now-previous)/1000,.05);
    previous=now;
    const box=canvas.getBoundingClientRect(),scale=Math.min(devicePixelRatio,1.4,1100/box.width);
    const width=Math.round(box.width*scale),height=Math.round(box.height*scale);
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;gl.viewport(0,0,width,height);}
    gl.uniform2f(uniforms.resolution,width,height);gl.uniform1f(uniforms.time,elapsed);gl.uniform1f(uniforms.subject,subject);gl.uniform2f(uniforms.turn,...turn);
    gl.drawArrays(gl.TRIANGLES,0,6);
    if(moving)frame=requestAnimationFrame(draw);
  }
  function request(){if(!frame&&available)frame=requestAnimationFrame(draw);}
  function setMoving(value){moving=value;previous=0;if(frame){cancelAnimationFrame(frame);frame=0;}request();}
  const signal=()=>document.dispatchEvent(new CustomEvent('sculpture-state'));
  canvas.addEventListener('pointerdown',event=>{drag={x:event.clientX,y:event.clientY,turn:[...turn]};canvas.setPointerCapture(event.pointerId);});
  canvas.addEventListener('pointermove',event=>{if(!drag)return;turn=[drag.turn[0]+(event.clientX-drag.x)*.006,drag.turn[1]+(event.clientY-drag.y)*.006];request();});
  canvas.addEventListener('pointerup',()=>{drag=null;});canvas.addEventListener('pointercancel',()=>{drag=null;});
  canvas.addEventListener('keydown',event=>{const keys={ArrowLeft:[-.16,0],ArrowRight:[.16,0],ArrowUp:[0,-.16],ArrowDown:[0,.16]};if(keys[event.key]){event.preventDefault();turn=turn.map((v,i)=>v+keys[event.key][i]);request();}});
  document.addEventListener('visibilitychange',()=>{previous=0;request();});
  new ResizeObserver(request).observe(canvas);
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;previous=0;if(visible)request();}).observe(canvas);
  reduced.addEventListener('change',event=>{if(event.matches){setMoving(false);signal();}});
  canvas.addEventListener('webglcontextlost',()=>{available=false;setMoving(false);signal();});
  window.sculpture={get available(){return available;},get moving(){return moving;},setSubject(index){subject=index;request();},toggle(){setMoving(!moving);signal();},reset(){turn=[0,0];elapsed=2.4;request();}};
  request();
})();
