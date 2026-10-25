import { type ReactNode, useEffect, useRef } from 'react';
import { Camera, Geometry, Mesh, Program, Renderer } from 'ogl';
import StrokeText from './StrokeText';

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const PARTICLE_VERT = `attribute vec3 position; attribute vec4 random; attribute vec3 color;
uniform mat4 modelMatrix, viewMatrix, projectionMatrix; uniform float uTime, uSpread, uSize;
varying vec3 vColor; void main(){ vColor=color; vec3 p=position*uSpread; p.x+=sin(uTime*random.z+random.w*6.28)*random.x; p.y+=sin(uTime*random.y+random.x*6.28)*random.w; vec4 mv=viewMatrix*modelMatrix*vec4(p,1.); gl_PointSize=uSize/length(mv.xyz); gl_Position=projectionMatrix*mv; }`;
const PARTICLE_FRAG = `precision highp float; varying vec3 vColor; void main(){ float d=length(gl_PointCoord-vec2(.5)); float a=smoothstep(.5,.28,d)*.58; gl_FragColor=vec4(vColor,a); }`;

export function ParticlesBackground() {
  const targetRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const target = targetRef.current;
    if (!target || prefersReducedMotion() || window.innerWidth < 720) return;
    let renderer: Renderer;
    try { renderer = new Renderer({ dpr: Math.min(window.devicePixelRatio || 1, 1.5), depth: false, alpha: true }); } catch { return; }
    const gl = renderer.gl; gl.clearColor(0, 0, 0, 0);
    const count = 84;
    const positions = new Float32Array(count * 3); const randoms = new Float32Array(count * 4); const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      positions.set([(Math.random() - .5) * 2, (Math.random() - .5) * 2, (Math.random() - .5) * 2], i * 3);
      randoms.set([Math.random(), Math.random(), Math.random(), Math.random()], i * 4);
      colors.set(i % 3 === 0 ? [.25, .78, .82] : [.40, .55, .61], i * 3);
    }
    const camera = new Camera(gl, { fov: 16 }); camera.position.set(0, 0, 20);
    const geometry = new Geometry(gl, { position: { size: 3, data: positions }, random: { size: 4, data: randoms }, color: { size: 3, data: colors } });
    const program: any = new Program(gl, { vertex: PARTICLE_VERT, fragment: PARTICLE_FRAG, uniforms: { uTime: { value: 0 }, uSpread: { value: 8 }, uSize: { value: 54 } }, transparent: true, depthTest: false });
    const particles = new Mesh(gl, { mode: gl.POINTS, geometry, program }); target.appendChild(gl.canvas);
    const resize = () => { renderer.setSize(target.clientWidth, target.clientHeight); camera.perspective({ aspect: gl.canvas.width / gl.canvas.height }); };
    resize(); window.addEventListener('resize', resize);
    let frame = 0; let started = performance.now(); let visible = !document.hidden;
    const draw = (now: number) => {
      if (!visible) { frame = 0; return; }
      frame = requestAnimationFrame(draw);
      program.uniforms.uTime.value = (now - started) * .00004; particles.rotation.y = (now - started) * .00001; renderer.render({ scene: particles, camera });
    };
    const onVisibility = () => { visible = !document.hidden; if (visible && !frame) frame = requestAnimationFrame(draw); };
    document.addEventListener('visibilitychange', onVisibility);
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('visibilitychange', onVisibility); window.removeEventListener('resize', resize); if (target.contains(gl.canvas)) target.removeChild(gl.canvas); gl.getExtension('WEBGL_lose_context')?.loseContext(); };
  }, []);
  return <div ref={targetRef} className="particles-background" aria-hidden="true" />;
}

export function ElectricBorder({ children, className = '', color = '#66e2e5', borderRadius = 12 }: { children: ReactNode; className?: string; color?: string; borderRadius?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null); const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current; const container = containerRef.current;
    const context = canvas?.getContext('2d'); if (!canvas || !container || !context || prefersReducedMotion()) return;
    let width = 1; let height = 1; let frame = 0;
    const resize = () => { const rect = container.getBoundingClientRect(); const dpr = Math.min(window.devicePixelRatio || 1, 2); width = rect.width; height = rect.height; canvas.width = width * dpr; canvas.height = height * dpr; canvas.style.width = `${width}px`; canvas.style.height = `${height}px`; context.setTransform(dpr, 0, 0, dpr, 0, 0); };
    const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(container); resize();
    // Only animate while the border is actually on screen — three of these
    // canvases run continuously in the verdict strip, and a 60fps 2D loop for
    // an element the user has scrolled past is wasted work.
    let onScreen = true;
    const visibilityObserver = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting;
      if (onScreen && !frame) frame = requestAnimationFrame(draw);
    }, { rootMargin: '200px' });
    visibilityObserver.observe(container);
    const draw = (time: number) => {
      if (!onScreen) { frame = 0; return; }
      frame = requestAnimationFrame(draw); context.clearRect(0, 0, width, height); const jitter = Math.sin(time * .004) * .6; context.beginPath(); context.roundRect(1.5 + jitter, 1.5, Math.max(0, width - 3), Math.max(0, height - 3), borderRadius); context.strokeStyle = color; context.globalAlpha = .60; context.lineWidth = 1.2; context.shadowColor = color; context.shadowBlur = 10; context.stroke(); context.shadowBlur = 0; context.globalAlpha = 1; };
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); resizeObserver.disconnect(); visibilityObserver.disconnect(); };
  }, [borderRadius, color]);
  return <div ref={containerRef} className={`electric-value ${className}`} style={{ borderRadius }}><canvas ref={canvasRef} aria-hidden="true" />{children}</div>;
}

// Every heading renders as a GSAP stroke-draw wordmark: the outline traces
// itself in, then the fill wipes across — the same "structured evidence"
// aesthetic as the rest of the console.
export function MatrixHeading({ text, as: Tag = 'h2', className = '' }: { text: string; as?: 'h1' | 'h2' | 'h3'; className?: string }) {
  const large = Tag === 'h1';
  return (
    <Tag className={`matrix-heading ${className}`} aria-label={text}>
      <StrokeText
        text={text}
        strokeColor="#6fe3e5"
        fillColor="#efffff"
        strokeWidth={large ? 1.6 : 0.9}
        drawDuration={large ? 2 : 0.9}
        fillDelay={large ? 0.4 : 0.15}
        stagger={large ? 0.05 : 0.03}
        ease="power2.out"
        trigger="mount"
        fillMode="wipe"
        fontSize={large ? 84 : 17}
        fontWeight={800}
        letterSpacing={large ? 1 : 0.5}
        className={large ? 'matrix-heading__hero' : 'matrix-heading__label'}
      />
    </Tag>
  );
}
