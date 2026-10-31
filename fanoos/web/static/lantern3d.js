/* Fanoos: cinematic 3D lantern (Three.js, no build step).
 *
 *   import { mountLantern } from "/static/lantern3d.js";
 *   const lantern = mountLantern(containerEl, { reducedMotion });
 *   lantern.setScroll(0..1);   // drive the camera from page scroll
 *   lantern.setMode("thinking" | "done" | "idle");   // react to the review state
 *   lantern.setFraming(x, y);  // place the lantern beside the content
 *   lantern.dispose();
 *
 * Everything is procedural: brass frame, glass globe, a living flame (shader), embers, bloom.
 * Returns null when WebGL is unavailable so the caller can keep its static fallback.
 */
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const BG = 0x0c0a09;
const BRASS = 0xb98a4a;
const FLAME_HOT = new THREE.Color(0xfff1c9);
const FLAME_WARM = new THREE.Color(0xf59e0b);
const FLAME_EDGE = new THREE.Color(0xd9480f);

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const clamp01 = (v) => Math.min(1, Math.max(0, v));

/** Smooth value noise for flicker, 0..1. */
function flicker(t, seed = 0) {
  return (
    0.55 +
    0.22 * Math.sin(t * 7.3 + seed) +
    0.13 * Math.sin(t * 13.1 + seed * 2.1) +
    0.1 * Math.sin(t * 23.7 + seed * 3.7)
  );
}

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGL2RenderingContext && c.getContext("webgl2"));
  } catch {
    return false;
  }
}

/* ---------------------------------------------------------------------------------------------- */
/* Geometry                                                                                         */
/* ---------------------------------------------------------------------------------------------- */

/** Profile of the glass globe (x = radius, y = height). */
function globeProfile() {
  const pts = [];
  const n = 40;
  for (let i = 0; i <= n; i++) {
    const t = i / n; // 0 bottom → 1 top
    const y = 0.32 + t * 1.02;
    const bulge = Math.sin(Math.PI * Math.pow(t, 0.92));
    const r = 0.3 + 0.27 * bulge - 0.04 * t;
    pts.push(new THREE.Vector2(r, y));
  }
  return pts;
}

function buildLantern(envMap, quality) {
  const group = new THREE.Group();

  const brass = new THREE.MeshStandardMaterial({ color: BRASS, metalness: 1, roughness: 0.32, envMapIntensity: 0.9, fog: false });
  const darkBrass = new THREE.MeshStandardMaterial({ color: 0x6b4a24, metalness: 1, roughness: 0.45, envMapIntensity: 0.7, fog: false });

  // Base: stepped, bevelled disc.
  const base = new THREE.Mesh(
    new THREE.LatheGeometry(
      [
        [0, 0], [0.5, 0], [0.54, 0.03], [0.54, 0.09], [0.48, 0.12], [0.42, 0.13],
        [0.42, 0.2], [0.38, 0.24], [0.33, 0.27], [0.32, 0.32], [0, 0.32],
      ].map(([x, y]) => new THREE.Vector2(x, y)),
      96,
    ),
    brass,
  );
  base.receiveShadow = true; // only the ribs cast shadows: radial light streaks on the floor
  group.add(base);

  // Glass globe.
  // Thin clear glass: reflections and a clearcoat sheen; transparent so the flame glow passes through.
  const glassMat = new THREE.MeshPhysicalMaterial({
    color: 0xfff1dc,
    metalness: 0,
    roughness: 0.06,
    transparent: true,
    opacity: 0.16,
    envMap,
    envMapIntensity: 0.9,
    clearcoat: 1,
    clearcoatRoughness: 0.04,
    specularIntensity: 1,
    side: THREE.DoubleSide,
    depthWrite: false,
    fog: false,
  });
  const glass = new THREE.Mesh(new THREE.LatheGeometry(globeProfile(), 96), glassMat);
  glass.renderOrder = 2;
  group.add(glass);

  // Brass ribs following the globe, slightly outside it.
  const profile = globeProfile();
  const ribCount = 6;
  for (let i = 0; i < ribCount; i++) {
    const a = (i / ribCount) * Math.PI * 2;
    const curve = new THREE.CatmullRomCurve3(
      profile.filter((_, k) => k % 4 === 0 || k === profile.length - 1).map(
        (p) => new THREE.Vector3(Math.cos(a) * (p.x + 0.025), p.y, Math.sin(a) * (p.x + 0.025)),
      ),
    );
    const rib = new THREE.Mesh(new THREE.TubeGeometry(curve, 64, 0.016, 10, false), brass);
    rib.castShadow = true;
    group.add(rib);
  }
  // Rings at the bottom and top of the globe.
  for (const [y, r] of [[0.33, 0.315], [1.33, 0.27]]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(r, 0.03, 16, 96), brass);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = y;
    ring.castShadow = true;
    group.add(ring);
  }

  // Cap: dome with ventilation ridge and a finial.
  const cap = new THREE.Mesh(
    new THREE.LatheGeometry(
      [
        [0, 1.6], [0.08, 1.6], [0.12, 1.57], [0.2, 1.5], [0.3, 1.43], [0.36, 1.39], [0.36, 1.36], [0.28, 1.34], [0, 1.34],
      ].map(([x, y]) => new THREE.Vector2(x, y)),
      96,
    ),
    brass,
  );
  cap.castShadow = true;
  group.add(cap);
  const finial = new THREE.Mesh(new THREE.SphereGeometry(0.055, 32, 16), brass);
  finial.position.y = 1.64;
  group.add(finial);

  // Handle: a bail arc, pivoting on the finial.
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.022, 16, 80, Math.PI), darkBrass);
  handle.position.y = 1.64;
  handle.castShadow = true;
  group.add(handle);

  // Wick holder.
  const burner = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 0.12, 32), darkBrass);
  burner.position.y = 0.38;
  group.add(burner);
  const wick = new THREE.Mesh(
    new THREE.CylinderGeometry(0.008, 0.008, 0.06, 8),
    new THREE.MeshBasicMaterial({ color: 0x1a1008, fog: false }),
  );
  wick.position.y = 0.47;
  group.add(wick);

  // Flame: two additive shells shaped by a vertex shader (teardrop that narrows into an upward point).
  const flameUniforms = { uTime: { value: 0 }, uIgnite: { value: 0 } };
  const flame = new THREE.Group();
  flame.position.y = 0.5;
  const flameGeo = new THREE.SphereGeometry(1, 48, 32);
  const makeShell = (scale, colorA, colorB, opacity) => {
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        ...flameUniforms,
        uColorA: { value: colorA },
        uColorB: { value: colorB },
        uOpacity: { value: opacity },
      },
      vertexShader: /* glsl */ `
        uniform float uTime; uniform float uIgnite;
        varying float vY; varying vec3 vN; varying vec3 vView;
        void main() {
          vec3 p = position;
          float y = p.y * 0.5 + 0.5;                       // 0 bottom → 1 tip
          float taper = mix(1.0, 0.0, pow(y, 1.6));        // teardrop: narrow to a point
          p.xz *= taper * (0.9 + 0.1 * sin(uTime * 9.0 + y * 6.0));
          p.y = (y * 2.6 - 0.6);                           // stretch upward
          float sway = sin(uTime * 2.3 + y * 3.0) * 0.06 + sin(uTime * 5.1) * 0.025;
          p.x += sway * y * y;
          p.z += cos(uTime * 1.9 + y * 2.0) * 0.04 * y * y;
          p *= uIgnite;
          vY = y;
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          vN = normalize(normalMatrix * normal);
          vView = normalize(-mv.xyz);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uColorA; uniform vec3 uColorB; uniform float uOpacity; uniform float uTime;
        varying float vY; varying vec3 vN; varying vec3 vView;
        void main() {
          float facing = pow(abs(dot(vN, vView)), 1.4);   // soft edges
          vec3 col = mix(uColorA, uColorB, smoothstep(0.05, 0.95, vY));
          float alpha = facing * (1.0 - smoothstep(0.7, 1.0, vY)) * uOpacity;
          alpha *= 0.85 + 0.15 * sin(uTime * 17.0 + vY * 10.0);
          gl_FragColor = vec4(col * 1.25, alpha);
        }`,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const shell = new THREE.Mesh(flameGeo, mat);
    shell.scale.setScalar(scale);
    return shell;
  };
  flame.add(makeShell(0.13, FLAME_WARM, FLAME_EDGE, 0.55));
  flame.add(makeShell(0.085, FLAME_HOT, FLAME_WARM, 0.8));
  flame.add(makeShell(0.04, new THREE.Color(0xffffff), FLAME_HOT, 0.9));
  group.add(flame);

  // Soft halo inside the glass.
  const halo = new THREE.Mesh(
    new THREE.SphereGeometry(0.42, 32, 16),
    new THREE.ShaderMaterial({
      uniforms: { uStrength: { value: 0 } },
      vertexShader: `varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix*vec4(position,1.); vN=normalize(normalMatrix*normal); vV=normalize(-mv.xyz); gl_Position=projectionMatrix*mv; }`,
      fragmentShader: `uniform float uStrength; varying vec3 vN; varying vec3 vV; void main(){ float f=pow(abs(dot(vN,vV)),3.0); gl_FragColor=vec4(vec3(1.0,0.62,0.2)*f*uStrength, f*uStrength*0.5); }`,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  halo.position.y = 0.72;
  group.add(halo);

  // Light from the flame.
  const light = new THREE.PointLight(0xffa340, 0, 9, 1.6);
  light.position.y = 0.66;
  if (quality.shadows) {
    light.castShadow = true;
    light.shadow.mapSize.set(1024, 1024);
    light.shadow.bias = -0.002;
    light.shadow.radius = 4;
  }
  group.add(light);

  // Camera-facing glow around the flame: gives warmth even when bloom is off.
  const glowTex = (() => {
    const c = document.createElement("canvas");
    c.width = c.height = 128;
    const g = c.getContext("2d");
    const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, "rgba(255,214,150,1)");
    grad.addColorStop(0.18, "rgba(255,160,60,0.55)");
    grad.addColorStop(0.5, "rgba(217,100,20,0.12)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  })();
  const glow = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: glowTex, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, transparent: true, opacity: 0, fog: false }),
  );
  glow.position.y = 0.62;
  glow.renderOrder = 3;
  group.add(glow);

  return { group, flame, flameUniforms, halo, light, glassMat, glow };
}

/** Rising embers around the lantern. */
function buildEmbers(count) {
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(count * 3);
  const seed = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 3.2;
    pos[i * 3 + 1] = Math.random() * 3.2 - 0.2;
    pos[i * 3 + 2] = (Math.random() - 0.5) * 2.4;
    seed[i] = Math.random();
  }
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
  const mat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uPixel: { value: Math.min(window.devicePixelRatio, 2) }, uFade: { value: 0 } },
    vertexShader: /* glsl */ `
      attribute float aSeed; uniform float uTime; uniform float uPixel; varying float vA;
      void main() {
        vec3 p = position;
        float life = fract(aSeed + uTime * (0.04 + aSeed * 0.05));
        p.y = mix(-0.2, 3.2, life);
        p.x += sin(uTime * 0.6 + aSeed * 40.0) * 0.18 * life;
        p.z += cos(uTime * 0.5 + aSeed * 30.0) * 0.12 * life;
        vA = sin(life * 3.14159) * (0.35 + aSeed * 0.65);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_PointSize = (2.0 + aSeed * 4.0) * uPixel * (3.0 / -mv.z);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */ `
      uniform float uFade; varying float vA;
      void main() {
        float d = length(gl_PointCoord - 0.5);
        float a = smoothstep(0.5, 0.0, d) * vA * uFade;
        gl_FragColor = vec4(1.0, 0.66, 0.28, a);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  return new THREE.Points(geo, mat);
}

/* ---------------------------------------------------------------------------------------------- */
/* Scene                                                                                            */
/* ---------------------------------------------------------------------------------------------- */

export function mountLantern(container, { reducedMotion = false, quality: qualityMode = "auto", onReady } = {}) {
  if (!webglAvailable()) return null;

  const small = window.matchMedia("(max-width: 720px)").matches;
  const quality = { shadows: !small && qualityMode !== "low", bloom: qualityMode !== "low", embers: small ? 70 : 160, pixelRatio: Math.min(window.devicePixelRatio, small ? 1.5 : 1.75) };

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  } catch {
    return null;
  }
  renderer.setPixelRatio(quality.pixelRatio);
  renderer.setClearColor(BG, 1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = quality.shadows;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.domElement.setAttribute("aria-hidden", "true");
  renderer.domElement.className = "lantern-canvas";
  container.append(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.fog = new THREE.FogExp2(BG, 0.16);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envMap;
  scene.environmentIntensity = 0.28;

  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 60);

  // Hanging rig: pivot at the handle so the lantern sways like a pendulum.
  const rig = new THREE.Group();
  rig.position.y = 1.7;
  scene.add(rig);
  const lantern = buildLantern(envMap, quality);
  lantern.group.position.y = -1.7;
  rig.add(lantern.group);

  // Chain up out of frame.
  const chainMat = new THREE.MeshStandardMaterial({ color: 0x5a4022, metalness: 1, roughness: 0.5, fog: false });
  for (let i = 0; i < 48; i++) { // long enough to leave the top of the frame
    const link = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.011, 8, 20), chainMat);
    link.position.y = 0.2 + i * 0.075;
    link.rotation.y = i % 2 ? Math.PI / 2 : 0;
    rig.add(link);
  }

  // Ground that catches the warm light and the rib shadows.
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(40, 64),
    new THREE.MeshStandardMaterial({ color: 0x241b14, roughness: 0.88, metalness: 0 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.62;
  ground.receiveShadow = true;
  scene.add(ground);

  // Cool rim light from behind for a cinematic silhouette; faint warm fill.
  const rim = new THREE.DirectionalLight(0x9bb4ff, 0.5);
  rim.position.set(-3, 3, -4);
  scene.add(rim);
  const fill = new THREE.HemisphereLight(0x3a2a1a, 0x050403, 0.35);
  scene.add(fill);

  const embers = buildEmbers(quality.embers);
  embers.position.y = -0.6;
  scene.add(embers);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.5, 0.45, 0.86);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  /* State ----------------------------------------------------------------------------------- */
  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  let scroll = 0;
  let smoothScroll = 0;
  let visible = true;
  let running = false;
  let disposed = false;
  let compiledReady = false;
  let raf = 0;
  const timer = new THREE.Timer();
  const perf = { frames: 0, since: 0, checked: false };
  const introDuration = reducedMotion ? 0 : 3.2;
  let readyFired = false;
  let introStart = -1;
  // Review state: "thinking" makes the flame work harder; "done" flares once.
  let mode = "idle";
  let energy = 0;
  let flare = 0;
  let lastT = 0;
  let flameTime = 0;
  let emberTime = 0;
  const framing = { x: 0, y: 0 };

  function resize() {
    const w = container.clientWidth || 1;
    const h = container.clientHeight || 1;
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    bloom.resolution.set(w, h);
    camera.aspect = w / h;
    // Keep the lantern framed on tall/narrow screens.
    camera.fov = w / h < 0.8 ? 42 : 32;
    // Shift the lantern within the frame (e.g. beside the headline) without moving the camera.
    camera.setViewOffset(w, h, -framing.x * w, -framing.y * h, w, h);
    camera.updateProjectionMatrix();
  }

  function frame(t) {
    // The intro is timed from the first frame actually shown, not from page load.
    const ti = t - introStart;
    const intro = introDuration ? clamp01(ti / introDuration) : 1;
    const ignite = introDuration ? easeOutCubic(clamp01((ti - 0.5) / 1.4)) : 1;
    const rawDt = Math.max(0, t - lastT);
    const dt = Math.min(0.1, rawDt); // capped for the flame/energy integrators
    lastT = t;
    energy += ((mode === "thinking" ? 1 : 0) - energy) * Math.min(1, dt * 2.5);
    flare *= Math.exp(-dt * 2.2);
    flameTime += dt * (1 + 0.9 * energy);
    emberTime += dt * (1 + 2.4 * energy);

    // Camera: dolly out from a close, low shot; then parallax + scroll orbit.
    // Time-based easing: the same feel at 30, 60 or 120 fps.
    const ease = 1 - Math.exp(-Math.min(0.5, rawDt) * 3);
    pointer.x += (pointer.tx - pointer.x) * ease;
    pointer.y += (pointer.ty - pointer.y) * ease;
    smoothScroll += (scroll - smoothScroll) * (1 - Math.exp(-Math.min(0.5, rawDt) * 5));
    const k = easeInOut(intro);
    const far = camera.aspect < 0.8 ? 10.5 : 8.2; // pull back on tall screens so the whole lantern fits
    const dist = THREE.MathUtils.lerp(2.4, far, k) + smoothScroll * 1.8 - energy * 0.9;
    const orbit = pointer.x * 0.35 + smoothScroll * 0.9 + (1 - k) * -0.5;
    const height = THREE.MathUtils.lerp(0.35, 1.0, k) + pointer.y * 0.25 - smoothScroll * 0.4;
    camera.position.set(Math.sin(orbit) * dist, height, Math.cos(orbit) * dist);
    camera.lookAt(0, THREE.MathUtils.lerp(0.5, 0.62, k), 0);

    // Pendulum sway.
    const sway = reducedMotion ? 0 : Math.sin(t * 0.9) * 0.035 + Math.sin(t * 0.37) * 0.015;
    rig.rotation.z = sway;
    rig.rotation.x = reducedMotion ? 0 : Math.cos(t * 0.7) * 0.02;
    lantern.group.rotation.y = reducedMotion ? 0.4 : t * 0.12;

    // Flame and light.
    const f = reducedMotion ? 0.7 : flicker(flameTime);
    const boost = 1 + 0.4 * energy + 1.1 * flare;
    lantern.flameUniforms.uTime.value = flameTime;
    lantern.flameUniforms.uIgnite.value = ignite * (0.94 + 0.06 * f) * (1 + 0.2 * energy + 0.3 * flare);
    lantern.light.intensity = ignite * (4 + 1.9 * f) * boost;
    lantern.halo.material.uniforms.uStrength.value = ignite * (0.12 + 0.07 * f);
    bloom.strength = quality.bloom ? 0.3 + 0.4 * ignite : 0;
    lantern.glow.material.opacity = Math.min(1, ignite * (quality.bloom ? 0.35 : 0.6) * (0.85 + 0.15 * f) * boost);
    lantern.glow.scale.setScalar((quality.bloom ? 2.2 : 2.8) + 0.12 * f);

    embers.material.uniforms.uTime.value = emberTime;
    embers.material.uniforms.uFade.value = ignite;

    composer.render();
  }

  // Weak GPU? After the intro, drop shadows, bloom and resolution so the page stays smooth.
  function adapt(t) {
    if (perf.checked || qualityMode === "high") return;
    if (!perf.since) perf.since = t;
    perf.frames++;
    if (t - perf.since < 2.5) return;
    perf.checked = true;
    const fps = perf.frames / (t - perf.since);
    if (fps < 40) {
      quality.bloom = false;
      renderer.shadowMap.enabled = false;
      lantern.light.castShadow = false;
      renderer.setPixelRatio(1);
      resize();
      container.dataset.quality = "low";
    }
  }

  function loop() {
    raf = requestAnimationFrame(loop);
    timer.update();
    const t = timer.getElapsed();
    if (introStart < 0) introStart = t;
    frame(t);
    adapt(t);
    if (!readyFired) {
      readyFired = true;
      container.classList.add("is-lit");
      onReady?.();
    }
  }

  function start() {
    if (running || reducedMotion || !compiledReady || disposed) return;
    running = true;
    container.dataset.state = "running";
    loop();
  }
  function stop() {
    running = false;
    container.dataset.state = "paused";
    cancelAnimationFrame(raf);
  }

  const onPointer = (e) => {
    const r = container.getBoundingClientRect();
    pointer.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    pointer.ty = -((e.clientY - r.top) / r.height - 0.5) * 2;
  };
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  const io = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible && !document.hidden) start();
    else stop();
  });
  io.observe(container);
  const onVisibility = () => (document.hidden || !visible ? stop() : start());
  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("pointermove", onPointer, { passive: true });

  resize();
  if (reducedMotion) {
    introStart = 0;
    container.dataset.state = "static";
    frame(10);
    container.classList.add("is-lit");
    onReady?.();
  } else {
    // Compile every shader before the first frame so the intro never stutters.
    // compileAsync only helps (and only stays quiet) where parallel compilation is supported.
    const parallel = renderer.extensions.has("KHR_parallel_shader_compile");
    if (!parallel) renderer.compile(scene, camera);
    const compiled = parallel ? renderer.compileAsync(scene, camera) : Promise.resolve();
    compiled
      .catch(() => {})
      .finally(() => {
        compiledReady = true;
        if (visible && !document.hidden) start();
      });
  }

  return {
    setScroll(v) {
      scroll = clamp01(v);
      if (reducedMotion) frame(10);
    },
    /** "idle" | "thinking" | "done" (a short flare, then idle). */
    setMode(next) {
      if (next === "done") {
        flare = 1;
        mode = "idle";
      } else {
        mode = next === "thinking" ? "thinking" : "idle";
      }
      container.dataset.mode = next;
      if (reducedMotion) frame(10);
    },
    /** Read-only snapshot of the scene state, for automated UI checks. */
    debug() {
      return {
        running,
        reducedMotion,
        mode,
        energy: +energy.toFixed(3),
        flare: +flare.toFixed(3),
        scroll: +smoothScroll.toFixed(3),
        pointer: { x: +pointer.x.toFixed(3), y: +pointer.y.toFixed(3) },
        intro: introStart < 0 ? 0 : +clamp01((lastT - introStart) / (introDuration || 1)).toFixed(3),
        ignited: introStart >= 0 && lastT - introStart > 1.9,
        quality: { ...quality, shadowsOn: renderer.shadowMap.enabled, low: container.dataset.quality === "low" },
        embers: quality.embers,
        lightIntensity: +lantern.light.intensity.toFixed(2),
        swayZ: +rig.rotation.z.toFixed(4),
        framing: { ...framing },
      };
    },
    /** Place the lantern in the frame: x/y are fractions of the width/height (+x right, +y down). */
    setFraming(x = 0, y = 0) {
      framing.x = x;
      framing.y = y;
      resize();
      if (reducedMotion) frame(10);
    },
    dispose() {
      disposed = true;
      stop();
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pointermove", onPointer);
      composer.dispose?.();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
