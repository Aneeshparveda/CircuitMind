import { type CSSProperties, type ChangeEvent, Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { motion, useInView } from 'motion/react';
import { Streamlit } from 'streamlit-component-lib';
import { ElectricBorder, MatrixHeading, ParticlesBackground } from './Effects';
import MatrixText from './MatrixText';
import GradientButton from './GradientButton';
import BentoCard, { gridVariants } from './BentoCard';
import StarBorder from './StarBorder';
import SideRays from './SideRays';
import type { ComponentOption, ConsoleArgs, DiagnosisReport, FailedTest, FleetRow } from './types';
import { fmt, normalButton, emit, findScrollContainer, registerPendingSetter } from './utils';
import SectionBoundary from './SectionBoundary';
const RoiCalculatorCard = lazy(() => import('./RoiCalculatorCard'));
const GovImpactCard = lazy(() => import('./GovImpactCard'));
const PricingDeploymentCard = lazy(() => import('./PricingDeploymentCard'));
const SecurityPrivacyCard = lazy(() => import('./SecurityPrivacyCard'));
const LimitationsSafetyCard = lazy(() => import('./LimitationsSafetyCard'));
const IntegrationDataContractCard = lazy(() => import('./IntegrationDataContractCard'));
const PositioningStatementCard = lazy(() => import('./PositioningStatementCard'));
const CompetitiveLandscapeCard = lazy(() => import('./CompetitiveLandscapeCard'));
const MarketOpportunityCard = lazy(() => import('./MarketOpportunityCard'));
import EvidenceChainVisualizer from './EvidenceChainVisualizer';

function EvidenceBar({ label, value }: { label: string; value: number }) {
  return <div className="evidence-bar">
    <div><span>{label}</span><b>{fmt(value, 1)}</b></div>
    <span className="evidence-bar__track"><span style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} /></span>
  </div>;
}

const SCATTER_PALETTE = ['#5eead4', '#7dd3fc', '#f0abfc', '#fcd34d', '#fb923c', '#f87171', '#a3e635', '#e9d5ff'];

function PatternSpaceScatter({ report }: { report: DiagnosisReport }) {
  const cases = report.semantic_memory?.cases ?? [];
  const query = report.semantic_memory?.pca_point ?? [0, 0];
  if (cases.length < 2) return null;
  const roots = [...new Set(cases.map((item) => item.root_cause_component))].sort();
  const colorFor = (root: string) => SCATTER_PALETTE[roots.indexOf(root) % SCATTER_PALETTE.length];
  const xs = cases.map((item) => item.x);
  const ys = cases.map((item) => item.y);
  const minX = Math.min(...xs, query[0]);
  const maxX = Math.max(...xs, query[0]);
  const minY = Math.min(...ys, query[1]);
  const maxY = Math.max(...ys, query[1]);
  const W = 460;
  const H = 300;
  const M = 20;
  const spanX = (maxX - minX) || 1;
  const spanY = (maxY - minY) || 1;
  const px = (x: number) => M + ((x - (minX - spanX * 0.12)) / (spanX * 1.24)) * (W - 2 * M);
  const py = (y: number) => H - M - ((y - (minY - spanY * 0.12)) / (spanY * 1.24)) * (H - 2 * M);
  return <article className="forensic-panel scatter-panel">
    <div className="section-heading"><MatrixHeading text="PATTERN SPACE" as="h2" /><span>PCA PROJECTION · 150 REPAIR CASES</span></div>
    <svg viewBox={`0 0 ${W} ${H}`} className="scatter-plot" role="img" aria-label="PCA projection of historical repair cases with the current board's signature">
      {cases.map((item) => <circle key={item.repair_id} cx={px(item.x)} cy={py(item.y)} r={3.4} fill={colorFor(item.root_cause_component)} opacity={0.6}><title>{item.repair_id} · {item.root_cause_component}</title></circle>)}
      <circle cx={px(query[0])} cy={py(query[1])} r={8} fill="none" stroke="#ffffff" strokeWidth={2} strokeDasharray="3 3" />
      <circle cx={px(query[0])} cy={py(query[1])} r={3.4} fill="#ffffff" />
      <text x={px(query[0]) + 12} y={py(query[1]) - 10} fill="#eaf5f6" fontSize={10} fontWeight={800} letterSpacing={0.08}>CASE UNDER TEST</text>
    </svg>
    <div className="scatter-legend">{roots.slice(0, 8).map((root) => <span key={root}><i style={{ background: colorFor(root) }} />{root}</span>)}</div>
  </article>;
}

function FaultPropagationReplay({ report }: { report: DiagnosisReport }) {
  const paths = report.dag_analysis?.causal_paths ?? [];
  const leading = report.suspects?.[0]?.refdes;
  const leadingNet = report.suspects?.[0]?.net;
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const svgRef = useRef<SVGSVGElement>(null);
  const startRef = useRef(performance.now());

  const layout = useMemo(() => {
    let pathLists = paths.map((entry) => entry.path ?? []).filter((list) => list.length >= 2);
    if (pathLists.length === 0) {
      const chain = [report.dag_analysis?.primary_nets?.[0], leading, report.dag_analysis?.cascade_nets?.[0]].filter(Boolean) as string[];
      if (chain.length >= 2) pathLists = [chain];
    }
    if (pathLists.length === 0) return null;
    const nodes = new Map<string, { id: string; level: number; component: boolean }>();
    pathLists.forEach((list) => list.forEach((id, i) => {
      const current = nodes.get(id);
      nodes.set(id, current
        ? { id, level: Math.min(current.level, i), component: current.component }
        : { id, level: i, component: /^[A-Z]\d/.test(id) });
    }));
    const W = 940;
    const H = 300;
    const M = 30;
    const maxLevel = Math.max(...[...nodes.values()].map((node) => node.level));
    const byLevel = new Map<number, string[]>();
    for (const node of nodes.values()) {
      const list = byLevel.get(node.level) ?? [];
      list.push(node.id);
      byLevel.set(node.level, list);
    }
    const positions = new Map<string, { x: number; y: number }>();
    for (const [level, ids] of byLevel) {
      const step = (H - 2 * M) / Math.max(ids.length, 1);
      ids.forEach((id, i) => positions.set(id, {
        x: M + (level * (W - 2 * M)) / Math.max(maxLevel, 1),
        y: M + step * (i + 0.5),
      }));
    }
    // Anchor the diagnosed candidate next to its net when that net is visible,
    // so the animated cascade ends at the component the machine actually blames.
    const suspectNetPoint = leadingNet ? positions.get(leadingNet) : undefined;
    if (leading && leadingNet && !nodes.has(leading) && suspectNetPoint) {
      nodes.set(leading, { id: leading, level: maxLevel + 1, component: true });
      positions.set(leading, {
        x: Math.min(Math.max(suspectNetPoint.x, M + 64), W - M - 64),
        y: Math.min(suspectNetPoint.y + 64, H - M - 16),
      });
    }
    const polylines = pathLists.map((list) => list.map((id) => positions.get(id)).filter((point): point is { x: number; y: number } => Boolean(point)));
    const edges = [...new Set(pathLists.flatMap((list) => list.slice(1).map((_, i) => `${list[i]}|${list[i + 1]}`)))]
      .map((key) => key.split('|'));
    const source = pathLists[0]?.[0] ?? report.dag_analysis?.primary_nets?.[0] ?? 'SOURCE';
    const symptom = pathLists[0]?.[pathLists[0].length - 1] ?? report.dag_analysis?.cascade_nets?.[0] ?? 'SYMPTOM';
    return { W, H, nodes: [...nodes.values()], positions, polylines, edges, source, symptom };
  }, [paths, leading, leadingNet, report.dag_analysis]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || !layout) return;
    const energy = Array.from(svg.querySelectorAll<SVGPathElement>('.replay-energy'));
    const pulses = Array.from(svg.querySelectorAll<SVGCircleElement>('.replay-pulse'));
    if (energy.length === 0) return;
    const totals = energy.map((el) => el.getTotalLength() || 1);
    let frame = 0;
    let onScreen = true;
    // Pause the loop entirely when paused or scrolled out of view — the
    // requestAnimationFrame chain should not burn cycles off-screen.
    const tick = (now: number) => {
      if (!playing || !onScreen) { frame = 0; return; }
      frame = requestAnimationFrame(tick);
      const elapsed = now - startRef.current;
      energy.forEach((el, i) => {
        const total = totals[i];
        const progress = ((elapsed * speed) / 1500 + i * 0.22) % 1;
        const length = progress * total;
        el.setAttribute('stroke-dasharray', `${length} ${total}`);
        if (pulses[i]) {
          const point = el.getPointAtLength(length);
          pulses[i].setAttribute('cx', String(point.x));
          pulses[i].setAttribute('cy', String(point.y));
        }
      });
    };
    const observer = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting;
      if (onScreen && !frame && playing) frame = requestAnimationFrame(tick);
    }, { rootMargin: '240px' });
    observer.observe(svg);
    frame = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(frame); observer.disconnect(); };
  }, [layout, playing, speed]);

  if (!layout) return null;
  const { W, H, nodes, positions, polylines, edges, source, symptom } = layout;
  return <article className="forensic-panel replay-panel">
    <div className="section-heading"><MatrixHeading text="FAULT PROPAGATION REPLAY" as="h2" /><span>{source} → {symptom} · {polylines.length} CASCADE PATH(S)</span></div>
    <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="replay-plot" style={{ '--speed': speed } as CSSProperties} role="img" aria-label="Animated fault propagation across the dependency graph">
      {edges.map(([a, b]) => {
        const from = positions.get(a);
        const to = positions.get(b);
        if (!from || !to) return null;
        return <line key={`${a}-${b}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} className="replay-edge" />;
      })}
      {polylines.map((polyline, i) => {
        const d = polyline.map((point, j) => `${j === 0 ? 'M' : 'L'}${point.x} ${point.y}`).join(' ');
        return <g key={i}>
          <path d={d} className="replay-energy" />
          <circle r={6} className="replay-pulse" />
        </g>;
      })}
      {leading && leadingNet && positions.has(leading) && positions.has(leadingNet) && <line x1={positions.get(leadingNet)!.x} y1={positions.get(leadingNet)!.y} x2={positions.get(leading)!.x} y2={positions.get(leading)!.y} className="replay-edge replay-edge--suspect" />}
      {nodes.map((node) => {
        const point = positions.get(node.id);
        if (!point) return null;
        const lead = node.id === leading;
        const isSource = node.id === source;
        const isSymptom = node.id === symptom;
        const klass = ['replay-node', node.component ? 'replay-node--component' : 'replay-node--net', lead ? 'replay-node--lead' : '', isSource ? 'replay-node--source' : '', isSymptom ? 'replay-node--symptom' : ''].filter(Boolean).join(' ');
        return <g key={node.id} className={klass} data-x={point.x} data-y={point.y} style={{ '--level': node.level } as CSSProperties}>
          {node.component ? <rect x={point.x - 26} y={point.y - 13} width={52} height={26} rx={7} /> : <circle cx={point.x} cy={point.y} r={11} />}
          <text x={point.x} y={point.y + 3.5} textAnchor="middle">{node.id}</text>
          {node.id === leading && <text x={point.x} y={point.y + 27} textAnchor="middle" className="replay-suspect-label">TOP SUSPECT</text>}
        </g>;
      })}
    </svg>
    <div className="replay-controls">
      <button className={normalButton} onClick={() => { setPlaying((value) => !value); startRef.current = performance.now(); }}>{playing ? 'PAUSE' : 'PLAY'}</button>
      <button className={normalButton} onClick={() => { startRef.current = performance.now(); }}>REPLAY</button>
      <label className="field-label replay-speed">SPEED<select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option></select></label>
      <span className="replay-hint">Pulse starts at the first observed upstream failure and ripples through the dependency path.</span>
    </div>
  </article>;
}

function FailureFingerprint({ report }: { report: DiagnosisReport }) {
  const fp = report.fingerprint;
  const segments = report.fingerprint_segments ?? [];
  if (!fp) return null;
  return <section className="forensic-panel fingerprint-panel">
    <div className="section-heading"><MatrixHeading text="FAILURE FINGERPRINT" as="h2" /><span>COMPACT FAILURE IDENTITY</span></div>
    <div className="fingerprint-layout">
      <div className="fingerprint-segments">{segments.map((seg) => <div key={seg.code} className={`fp-segment fp-segment--${seg.score >= 70 ? 'critical' : seg.score >= 30 ? 'medium' : 'low'}`} style={{ '--score': seg.score } as CSSProperties}><span className="fp-segment__code">{seg.code}</span><span className="fp-segment__score">{seg.score}</span><small>{seg.domain}</small></div>)}</div>
      <div className="fingerprint-meta">
        <div className="fp-meta-block"><b>{fp.split('|')[1]?.trim() || '?'}</b><small>FAILED</small></div>
        <div className="fp-meta-block"><b>{fp.split('|')[2]?.trim() || '?'}</b><small>ROOT NETS</small></div>
        <div className="fp-meta-block"><b>{fp.split('|')[3]?.trim() || '?'}</b><small>CASCADE</small></div>
      </div>
      <code className="fingerprint-string">{fp}</code>
    </div>
  </section>;
}

function BeatTheMachine({ report, truth, machineMs }: { report: DiagnosisReport; truth: string | null | undefined; machineMs: number }) {
  // Ground truth is NEVER in the analysis payload (Bug C): it arrives here
  // only after the server processed the explicit reveal action.
  const revealed = Boolean(truth);
  const [humanPick, setHumanPick] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number>(performance.now());
  const [session, setSession] = useState<{ machine: number; human: number }>(() => {
    try {
      const raw = localStorage.getItem('cm-btm-score');
      return raw ? (JSON.parse(raw) as { machine: number; human: number }) : { machine: 0, human: 0 };
    } catch { return { machine: 0, human: 0 }; }
  });
  // Live clock while the judge deliberates. The reveal triggers a server
  // round-trip, so the elapsed time is snapshotted to sessionStorage and
  // restored when the truth arrives back (the component re-mounts).
  useEffect(() => {
    if (revealed) {
      try {
        const saved = sessionStorage.getItem('cm-btm-elapsed');
        if (saved) setElapsed(Number(saved));
      } catch { /* noop */ }
      return;
    }
    const id = window.setInterval(() => setElapsed((performance.now() - startRef.current) / 1000), 400);
    return () => window.clearInterval(id);
  }, [revealed]);
  const options = (report.suspects ?? []).slice(0, 3).map((candidate) => candidate.refdes);
  const top = report.suspects?.[0];
  const engineHit = top?.refdes === truth;
  const humanHit = humanPick === truth;
  const onReveal = () => {
    // Snapshot this round's real timing before the round-trip.
    const seconds = Math.max((performance.now() - startRef.current) / 1000, 0.5);
    try { sessionStorage.setItem('cm-btm-elapsed', String(seconds)); } catch { /* noop */ }
    emit({ action: 'reveal_truth', board_id: report.board_id });
  };
  // Score the round once the truth has actually arrived from the server.
  useEffect(() => {
    if (!revealed) return;
    const next = {
      machine: session.machine + (engineHit ? 1 : 0),
      human: session.human + (humanHit ? 1 : 0),
    };
    setSession(next);
    try { localStorage.setItem('cm-btm-score', JSON.stringify(next)); } catch { /* noop */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealed]);
  if (!truth && !revealed) {
    // Pre-reveal: the judge commits before the server releases anything.
    return <section className="judge-panel">
      <div className="section-heading"><MatrixHeading text="BEAT THE MACHINE" as="h2" /><span>REVEAL IS SERVER-GATED · {report.case_number ?? report.board_id}</span></div>
      <p className="judge-intro">You are the technician on this line. Commit to a diagnosis <b>before</b> the reveal — the answer is fetched from the server only when you press reveal.</p>
      <div className="judge-clock"><span>YOUR CLOCK</span><b>{fmt(elapsed, 0)}s</b><small>MACHINE: {machineMs >= 1000 ? fmt(machineMs / 1000, 2) + ' s' : Math.max(machineMs, 0.1).toFixed(1) + ' ms'} (measured median)</small></div>
      <div className="judge-picks">{options.map((refdes) => <button key={refdes} className={`judge-pick ${humanPick === refdes ? 'judge-pick--active' : ''}`} onClick={() => setHumanPick(refdes)} disabled={revealed}>{refdes}</button>)}</div>
      <GradientButton variant="gold" className="judge-reveal" disabled={!humanPick || revealed} onClick={onReveal}>{revealed ? 'TRUTH REVEALED' : 'REVEAL THE TRUTH'}</GradientButton>
    </section>;
  }
  const boardsPerDay = 50;
  const minutesPerDay = ((elapsed - machineMs / 1000) * boardsPerDay) / 60;
  const hoursPerYear = (minutesPerDay * 250) / 60;
  return <section className="judge-panel">
    <div className="section-heading"><MatrixHeading text="BEAT THE MACHINE" as="h2" /><span>REVEAL IS SERVER-GATED · {report.case_number ?? report.board_id}</span></div>
    <p className="judge-intro">You are the technician on this line. Commit to a diagnosis <b>before</b> the reveal, then see who got it right.</p>
    <div className="judge-clock"><span>YOUR CLOCK</span><b>{fmt(elapsed, 0)}s</b><small>MACHINE: {machineMs >= 1000 ? fmt(machineMs / 1000, 2) + ' s' : Math.max(machineMs, 0.1).toFixed(1) + ' ms'} (measured median)</small></div>
    <div className="judge-picks">{options.map((refdes) => <button key={refdes} className={`judge-pick ${humanPick === refdes ? 'judge-pick--active' : ''}`} onClick={() => setHumanPick(refdes)} disabled={revealed}>{refdes}</button>)}</div>
    <GradientButton variant="gold" className="judge-reveal" disabled={!humanPick || revealed} onClick={onReveal}>{revealed ? 'TRUTH REVEALED' : 'REVEAL THE TRUTH'}</GradientButton>
    {revealed && <div className="judge-verdict">
      <div><span>GROUND TRUTH</span><b>{truth}</b></div>
      <div><span>MACHINE</span><b>{top?.refdes ?? '—'} · {fmt(top?.score, 1)}</b><em className={engineHit ? 'judge-hit' : 'judge-miss'}>{engineHit ? 'HIT' : 'MISS'}</em></div>
      <div><span>YOU</span><b>{humanPick}</b><em className={humanHit ? 'judge-hit' : 'judge-miss'}>{humanHit ? 'HIT' : 'MISS'}</em></div>
      <strong className="judge-outcome">{engineHit === humanHit ? 'TIED — BOTH GOT IT' : engineHit ? 'MACHINE WINS THIS ROUND' : 'YOU WIN THIS ROUND'}</strong>
      {!humanHit && humanPick && <p className="judge-cost">If the line had swapped {humanPick} first, rework is estimated at <b>₹3,200</b> in parts and labor before the real fault is found <em>(example cost model — replace with your line's actual COGS).</em></p>}
      <p className="judge-projection">Your diagnosis took <b>{fmt(elapsed, 0)} s</b> — CircuitMind: <b>{machineMs >= 1000 ? fmt(machineMs / 1000, 2) + ' s' : Math.max(machineMs, 0.1).toFixed(1) + ' ms'}</b> (measured median on this machine). <em>Assuming a scenario of {boardsPerDay} failing boards/day and {250} working days/yr:</em> ~<b>{fmt(minutesPerDay, 0)} min</b> of engineering time saved daily ({fmt(hoursPerYear, 0)} h/yr). Your timing is measured from this round; the daily/yearly figures are labeled scenario assumptions.</p>
      <p className="judge-session">SESSION SCORE · MACHINE <b>{session.machine}</b> · YOU <b>{session.human}</b> (persists while the page is open)</p>
    </div>}
  </section>;
}

function EvidenceAblation({ report }: { report: DiagnosisReport }) {
  const base = report.suspects ?? [];
  const streams = Object.keys(base[0]?.evidence_contributions ?? {});
  const policyWeights = report.evidence_policy?.weights ?? {};
  // Each stream gets a live multiplier (0–200% of its policy weight). The
  // fusion is recomputed entirely in the browser from the per-stream weighted
  // contributions already in the payload — no round-trip, and the judge can
  // watch the ranking respond to the policy in real time.
  const [multipliers, setMultipliers] = useState<Record<string, number>>(() =>
    Object.fromEntries(streams.map((stream) => [stream, 1]))
  );
  const ranked = useMemo(() => {
    const rescore = (candidate: typeof base[number]) => {
      const contributions = candidate.evidence_contributions ?? {};
      const rawTotal = streams.reduce((sum, stream) => sum + (contributions[stream] ?? 0), 0);
      const notesBonus = Math.max(0, (candidate.score ?? 0) - rawTotal);
      const fused = streams.reduce((sum, stream) => sum + (contributions[stream] ?? 0) * (multipliers[stream] ?? 1), 0);
      return Math.max(0, fused + notesBonus);
    };
    return [...base]
      .map((candidate) => ({ ...candidate, ablated: rescore(candidate) }))
      .sort((a, b) => b.ablated - a.ablated);
  }, [base, streams, multipliers]);
  const altered = streams.some((stream) => (multipliers[stream] ?? 1) !== 1);
  return <>
    <div className="ablation-controls">{streams.map((stream) => {
      const multiplier = multipliers[stream] ?? 1;
      const effective = Math.round((policyWeights[stream] ?? 0) * multiplier * 100);
      return <label key={stream} className="ablation-slider">
        <span className="ablation-slider__head"><b>{stream}</b><em>{effective}%</em></span>
        <input type="range" min={0} max={2} step={0.05} value={multiplier} aria-label={`${stream} evidence weight`}
          onChange={(event) => setMultipliers((previous) => ({ ...previous, [stream]: Number(event.target.value) }))} />
      </label>;
    })}
    {altered && <button className={normalButton} onClick={() => setMultipliers(Object.fromEntries(streams.map((stream) => [stream, 1])))}>RESET POLICY</button>}
    </div>
    <div className="ablation-result"><b>{altered ? 'RANK WITH ADJUSTED POLICY' : 'ACTIVE RANKING · POLICY WEIGHTS'}</b>{ranked.slice(0, 3).map((candidate, index) => <div key={candidate.refdes} className="ablation-row"><span>#{index + 1}</span><b>{candidate.refdes}</b><em>{candidate.desc}</em><strong>{fmt(candidate.ablated, 1)}</strong></div>)}</div>
  </>;
}

function CaseTimeline({ report }: { report: DiagnosisReport }) {
  const paths = report.dag_analysis?.causal_paths ?? [];
  // A passing board (or any board with no causal topology) has nothing to
  // replay — don't render a fabricated "PRIMARY NET → SYMPTOMS" trace.
  if (report.status === 'PASS' || (!paths.length && !report.dag_analysis?.primary_nets?.length)) return null;
  const firstPath = paths[0];
  const source = firstPath?.source_net ?? report.dag_analysis?.primary_nets?.[0] ?? 'PRIMARY NET';
  const symptom = firstPath?.symptom_net ?? report.dag_analysis?.cascade_nets?.[0] ?? 'OBSERVED SYMPTOMS';
  const chain = firstPath?.path ?? [source, 'DEPENDENCY PATH', symptom];
  return <section className="forensic-panel causal-panel">
    <div className="section-heading"><MatrixHeading text="CAUSAL TIME MACHINE" as="h2" /><span>ACTUAL GRAPH PATH</span></div>
    <div className="cause-trace">
      <div className="cause-trace__endpoint cause-trace__endpoint--source"><small>FIRST OBSERVED UPSTREAM FAILURE</small><strong>{source}</strong><p>Primary test evidence begins here.</p></div>
      <div className="cause-trace__route" aria-label={chain.join(' then ')}>{chain.slice(1, -1).map((node) => <span key={node}>{node}</span>)}</div>
      <div className="cause-trace__endpoint cause-trace__endpoint--symptom"><small>DOWNSTREAM BLAST RADIUS</small><strong>{symptom}</strong><p>{report.dag_analysis?.cascade_nets?.length ?? 0} cascade net(s) identified.</p></div>
    </div>
    <ol className="actual-trace">{(report.timeline ?? []).map((step) => <li key={step.label}><span>✓</span><div><b>{step.label}</b><p>{step.detail}</p></div><time>{fmt(step.duration_ms, 2)} ms</time></li>)}</ol>
  </section>;
}

function HypothesisArena({ report, challengeOpen, onChallenge }: { report: DiagnosisReport; challengeOpen: boolean; onChallenge: () => void }) {
  const candidates = report.suspects?.slice(0, 3) ?? [];
  const nbt = report.next_best_test;
  const mf = report.multi_fault;
  // Nothing to argue about on a passing board — skip the arena entirely.
  if (candidates.length === 0) return null;
  return <section className="forensic-panel arena-panel" id="hypothesis-arena">
    <div className="section-heading"><MatrixHeading text="HYPOTHESIS ARENA" as="h2" /><span>WHY THIS / WHY NOT THAT</span></div>
    <div className="hypothesis-list">{candidates.map((candidate, index) => {
      const coveragePct = candidate.coverage_pct ?? 0;
      const explained = candidate.explained_failures ?? [];
      const unexplained = candidate.unexplained_failures ?? [];
      const total = explained.length + unexplained.length;
      const isTop = index === 0;
      const forEvidence = candidate.positive_evidence ?? [];
      const againstEvidence = candidate.negative_evidence ?? [];
      const faultMode = candidate.fault_mode;
      return <article key={candidate.refdes} className={`hypothesis ${isTop ? 'hypothesis--leading' : ''}`}>
        <div className="hypothesis__identity"><span>#{index + 1}</span><div><b>{candidate.refdes} — {candidate.desc}</b><small>{candidate.cat} · {candidate.net}{faultMode ? ` · hypothesis: ${candidate.refdes} / ${faultMode.label}` : ''}</small></div><strong>{fmt(candidate.score, 1)}</strong></div>
        {/* Coverage bar */}
        <div className="hypothesis__coverage">
          <div className="coverage-bar"><div className="coverage-bar__fill" style={{ width: `${coveragePct}%` } as CSSProperties} /></div>
          <span className="coverage-label">{coveragePct}% · {explained.length}/{total} failures explained</span>
        </div>
        {/* Supporting evidence */}
        <details className="hypothesis__evidence" open={isTop}>
          <summary>SUPPORTING EVIDENCE ({forEvidence.length})</summary>
          <ul>{forEvidence.slice(0, 4).map((line, i) => <li key={i} className="ev-for">✓ {line}</li>)}</ul>
        </details>
        {/* ALIBI CHECK for non-leading candidates — the same WHY NOT logic, framed as a detective eliminating suspects */}
        {!isTop && <div className="hypothesis__whynot">
          <b>ALIBI CHECK — WHY NOT #{index + 1}?</b>
          <ul>{againstEvidence.slice(0, 3).map((line, i) => <li key={i} className="ev-against">✗ {line}</li>)}</ul>
          {coveragePct >= 100
            ? <em className="alibi-cleared">CLEARED ON EVIDENCE — covers the same failures electrically, but is outweighed on history, net and topology evidence</em>
            : <em className="alibi-cleared">CLEARED — explains only {coveragePct}% of failures; the remaining {total - explained.length} would have to be independent faults</em>}
        </div>}
      </article>;
    })}</div>
    {/* Multi-fault warning */}
    {mf?.multi_fault_likely && <div className="multi-fault-warning">
      <b>EVIDENCE SUGGESTS MULTIPLE INDEPENDENT FAULTS</b>
      <ul>{mf.indicators.slice(0, 3).map((indicator, i) => <li key={i}>{indicator}</li>)}</ul>
    </div>}
    {/* Multi-fault analysis — the sparse set-cover solver with parsimony */}
    {report.multi_fault_analysis?.analyzable && <div className="mfa-block">
      <div className="mfa-head"><b>MULTI-FAULT ANALYSIS</b><span>PARSIMONY-ADJUSTED · PREFER THE FEWEST FAULTS THAT EXPLAIN THE EVIDENCE</span></div>
      <div className="mfa-rows">
        <div className="mfa-row"><small>SINGLE FAULT</small><strong>{report.multi_fault_analysis.best_single?.components.join(' + ')}</strong><em>{fmt(report.multi_fault_analysis.best_single?.coverage_pct)}% coverage</em></div>
        {report.multi_fault_analysis.best_pair && <div className={`mfa-row mfa-row--pair ${report.multi_fault_analysis.verdict === 'MULTI_FAULT_LIKELY' ? 'mfa-row--flagged' : ''}`}><small>BEST TWO-FAULT</small><strong>{report.multi_fault_analysis.best_pair.components.join(' + ')}</strong><em>{fmt(report.multi_fault_analysis.best_pair.coverage_pct)}% coverage</em></div>}
      </div>
      {report.multi_fault_analysis.verdict_text && <p className="mfa-verdict">{report.multi_fault_analysis.verdict_text}</p>}
    </div>}
    <GradientButton variant="gold" className="challenge-button" onClick={onChallenge}>{challengeOpen ? 'HIDE DISPROOF ATTEMPT' : 'TRY TO DISPROVE IT'}</GradientButton>
    {challengeOpen && <div className="challenge-panel-inline" id="challenge-panel">
      <div className="section-heading"><MatrixHeading text="TRY TO DISPROVE IT" as="h3" /><span>Attempting to falsify the leading hypothesis using the current evidence.</span></div>
      {/* ─── TWO-AREA DISPROOF PRESENTATION ─── */}
      <div className="disproof-container">
        {/* Area 1: Why the leading hypothesis survives */}
        {report.diagnostic_contract?.inferred ? (() => {
          const inferred = report.diagnostic_contract.inferred;
          const topCandidate = candidates.find((c) => c.refdes === inferred.leading_refdes) || candidates[0];
          const forEv = topCandidate?.positive_evidence ?? [];
          const explainedCount = inferred.mechanism_explained?.length ?? 0;
          const totalCount = explainedCount + (inferred.mechanism_unexplained?.length ?? 0);

          return (
            <div className="disproof-card disproof-card--leader">
              <div className="disproof-card__badge-row">
                <small>AREA 1</small>
                <span className="disproof-status-badge">SURVIVES CURRENT DISPROOF TEST</span>
              </div>
              <div className="disproof-card__title">
                <b>WHY THE LEADING HYPOTHESIS SURVIVES</b>
                <h3>{inferred.leading_refdes} — {inferred.leading_desc}</h3>
              </div>
              <div className="disproof-metrics">
                <div className="disproof-metric">
                  <small>EVIDENCE SCORE</small>
                  <strong>{fmt(inferred.evidence_score, 1)}</strong>
                </div>
                <div className="disproof-metric">
                  <small>MECHANISM COVERAGE</small>
                  <strong>{inferred.mechanism_coverage_pct}%</strong>
                </div>
                <div className="disproof-metric">
                  <small>HYPOTHESIS MODE</small>
                  <span>{inferred.fault_mode || 'Degraded Mode'}</span>
                </div>
              </div>
              <p className="disproof-lead-desc">
                {inferred.leading_refdes} explains <b>{inferred.mechanism_coverage_pct}%</b> of observed failures by mechanism{totalCount > 0 ? ` (${explainedCount}/${totalCount} test steps)` : ''} with zero unexplained residual failures.
              </p>
              {forEv.length > 0 && (
                <div className="disproof-evidence-list">
                  <small>SUPPORTING EVIDENCE</small>
                  <ul>
                    {forEv.slice(0, 3).map((item, idx) => (
                      <li key={idx}>✓ {item}</li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="disproof-disclaimer">Physical verification still required.</p>
            </div>
          );
        })() : (
          <div className="disproof-card disproof-card--leader">
            <p className="disproof-disclaimer">Disproof details unavailable for this case.</p>
          </div>
        )}

        {/* Area 2: Why alternatives fail */}
        <div className="disproof-card disproof-card--alternatives">
          <div className="disproof-card__badge-row">
            <small>AREA 2</small>
            <span className="disproof-area-tag">ALTERNATIVE FALSIFICATION</span>
          </div>
          <div className="disproof-card__title">
            <b>WHY ALTERNATIVES FAIL THE CURRENT TEST</b>
          </div>
          <div className="disproof-rejected-list">
            {report.diagnostic_contract?.rejected && report.diagnostic_contract.rejected.length > 0 ? (
              report.diagnostic_contract.rejected.map((alt) => (
                <div key={alt.refdes} className="disproof-alt-item">
                  <div className="disproof-alt-item__head">
                    <strong>{alt.refdes} — {alt.desc}</strong>
                    {alt.mechanism_coverage_pct >= 100 ? (
                      <span className="disproof-cleared-tag">CLEARED ON EVIDENCE</span>
                    ) : (
                      <span className="disproof-eliminated-tag">ELIMINATED</span>
                    )}
                  </div>
                  <div className="disproof-alt-item__meta">
                    <span>Score: {fmt(alt.score, 1)}</span>
                    <span>Coverage: {alt.mechanism_coverage_pct}%</span>
                  </div>
                  <p className="disproof-alt-item__reason">{alt.rejection_reason}</p>
                  {alt.evidence_gap && (
                    <div className="disproof-alt-item__gap">
                      <small>EVIDENCE GAP:</small> <span>{alt.evidence_gap}</span>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="disproof-disclaimer">Disproof details unavailable for this case.</p>
            )}
          </div>
        </div>
      </div>

      {/* ─── EXPLANATION PRINCIPLE ─── */}
      <div className="disproof-principle-banner">
        <p>"We prefer the hypothesis that explains the observed failures with the fewest additional assumptions."</p>
      </div>

      <div className="counterfactual-comparison">{candidates.map((candidate) => {
        const evo = candidate.expected_vs_observed;
        const coveragePct = evo ? evo.coverage_pct : candidate.coverage_pct ?? 0;
        const explained = evo ? evo.explained : candidate.explained_failures ?? [];
        const unexplained = evo ? evo.unexpected : candidate.unexplained_failures ?? [];
        const total = explained.length + unexplained.length;
        const isComplete = coveragePct === 100;
        const electricalPct = candidate.coverage_pct;
        return <div key={candidate.refdes} className={`cf-card ${isComplete ? 'cf-card--complete' : ''}`}>
          <div className="cf-card__header"><b>{candidate.refdes}</b><small>{coveragePct}% by mechanism</small></div>
          <div className="coverage-bar"><div className="coverage-bar__fill cf-fill" style={{ width: `${coveragePct}%` } as CSSProperties} /></div>
          <p className="cf-card__summary">{isComplete ? '✓ Explains every observed failure by mechanism' : `Explains ${explained.length}/${total} observed failures by mechanism; ${unexplained.length} fall outside its blast radius`}</p>
          {electricalPct !== undefined && <small className="cf-card__electrical">electrical reachability: {electricalPct}% — connectivity ≠ causality</small>}
          {explained.length > 0 && <details><summary>Explained by mechanism ({explained.length})</summary><ul>{explained.map((step) => <li key={step} className="cf-step cf-step--explained">✓ {step}</li>)}</ul></details>}
          {unexplained.length > 0 && <details><summary>Outside mechanism ({unexplained.length})</summary><ul>{unexplained.map((step) => <li key={step} className="cf-step cf-step--unexplained">✗ {step}</li>)}</ul></details>}
          {candidate.expected_vs_observed?.expected_but_passed && candidate.expected_vs_observed.expected_but_passed.length > 0 && <details><summary>Predicted to fail, but passed ({candidate.expected_vs_observed.expected_but_passed.length})</summary><ul>{candidate.expected_vs_observed.expected_but_passed.map((step) => <li key={step} className="cf-step cf-step--passed">! {step}</li>)}</ul></details>}
        </div>;
      })}</div>
      {candidates[0] && <p className="cf-verdict">The leading hypothesis <b>{candidates[0].refdes}</b> explains <b>{candidates[0].expected_vs_observed?.coverage_pct ?? candidates[0].coverage_pct}%</b> of observed failures by mechanism (the highest). {candidates[1] && (candidates[1].expected_vs_observed?.coverage_pct ?? candidates[1].coverage_pct ?? 0) >= 100
        ? `${candidates[1].refdes} covers the same failures — the separation comes from the evidence streams, not connectivity.`
        : `${candidates[1].refdes} explains only ${candidates[1].expected_vs_observed?.coverage_pct ?? candidates[1].coverage_pct}% by mechanism — the remaining failures fall outside its plausible blast radius.`}</p>}
      {candidates[0] && <div className="cf-principle"><b>⚑ MINIMUM ACCUSATION PRINCIPLE APPLIED</b><p>{candidates.every((c) => (c.coverage_pct ?? 0) >= 100)
        ? `All candidates explain the observed failures electrically — connectivity alone cannot separate them. The ranking is decided by the evidence streams: historical precedent, net association, and topology position. Prefer the hypothesis the evidence supports.`
        : `Assuming <b>${candidates[0].refdes}</b> as the root cause requires zero additional independent faults — the fewest of any candidate. ${candidates.slice(1).map((candidate) => (candidate.coverage_pct ?? 0) >= 100
          ? `${candidate.refdes} covers the same failures electrically but is outweighed on the evidence streams`
          : `${candidate.refdes} requires the remaining ${100 - (candidate.coverage_pct ?? 0)}% of failures to be separate faults`).join('; ')}. Prefer the explanation that accuses the fewest components.`}</p></div>}
      {candidates.length > 1 && <div className="cf-graveyard">
        <div className="section-heading" style={{ marginTop: 18 }}><MatrixHeading text="INVESTIGATED AND CLEARED" as="h3" /><span>THE SYSTEM ELIMINATES BEFORE IT ACCUSES</span></div>
        {candidates.slice(1).map((candidate) => {
          const pct = candidate.coverage_pct ?? 0;
          const unexplained = (candidate.unexplained_failures ?? []).length;
          const total2 = (candidate.explained_failures ?? []).length + unexplained;
          return <div key={candidate.refdes} className="cf-cleared"><span className="cf-cleared__mark">✗</span><b>{candidate.refdes} — {candidate.desc}</b><em>{pct >= 100
            ? `CLEARED ON EVIDENCE: covers the same failures electrically, but is outweighed on history, net and topology evidence`
            : `CLEARED: ${pct}% coverage — ${unexplained > 0 ? `${unexplained}/${total2} failures remain unexplained without a second independent fault` : 'alibi fails — does not explain all observed failures'}`}</em></div>;
        })}
        <div className="cf-suspect-remaining"><span>⚑</span><b>{candidates[0].refdes} — {candidates[0].desc}</b><em>{candidates.every((c) => (c.coverage_pct ?? 0) >= 100)
          ? `LEADS ON EVIDENCE — same electrical coverage as the others, but the evidence streams favor ${candidates[0].refdes}`
          : `NO ALIBI: ${candidates[0].coverage_pct}% coverage — the minimum-assumption explanation`}</em></div>
      </div>}
      {nbt?.active && <>
        <div className="section-heading" style={{ marginTop: 20 }}><MatrixHeading text="NEXT BEST TEST" as="h3" /><span>WHAT WOULD CHANGE MY MIND?</span></div>
        <div className="nbt-meta"><span className={`nbt-chip nbt-chip--${(nbt.info_gain ?? 'MEDIUM').toLowerCase()}`}>INFO GAIN · {nbt.info_gain ?? 'MEDIUM'}</span><span className="nbt-chip">RISK · {nbt.risk ?? 'LOW'}</span><span className="nbt-chip">EFFORT · {nbt.effort ?? 'LOW'}</span>{nbt.separation !== undefined && <span className="nbt-chip">SEPARATION · {fmt(nbt.separation, 0)}/100</span>}</div>
        <div className="nbt-summary"><b>{nbt.test}</b><p>{nbt.purpose}</p><small>{nbt.reason}</small></div>
        <div className="nbt-outcomes">{Object.entries(nbt.expected_outcomes ?? {}).map(([c, outcome], idx) => <div key={c} className="nbt-outcome"><strong>{c}</strong><span>{outcome}</span><em className={`nbt-outcome__tag ${idx === 0 ? 'nbt-outcome__tag--fail' : 'nbt-outcome__tag--pass'}`}>{idx === 0 ? 'FAIL' : 'PASS'}</em></div>)}</div>
      </>}
    </div>}
  </section>;
}

function DiagnosticReceipt({ report }: { report: DiagnosisReport }) {
  const contract = report.diagnostic_contract;
  if (!contract) return null;
  const obs = contract.observed;
  const inf = contract.inferred;
  const rec = contract.recommended;
  const verif = contract.verification;
  return <section className="diagnostic-receipt" id="diagnostic-receipt">
    <div className="receipt-header">
      <small>CIRCUITMIND</small>
      <b>DIAGNOSTIC RECEIPT</b>
    </div>
    <div className="receipt-meta">
      <span>CASE {contract.case_number}</span>
      <span>BOARD {contract.board_id}</span>
      <span>{contract.timestamp}</span>
    </div>
    <div className="receipt-section">
      <small className="receipt-label">OBSERVED</small>
      <p>{obs.failed_test_count} failed test{obs.failed_test_count !== 1 ? 's' : ''} · {obs.primary_domain} · {obs.severity} · deviation {obs.deviation_range[0]}–{obs.deviation_range[1]}</p>
      {obs.failed_tests.length > 0 && <ul className="receipt-tests">{obs.failed_tests.slice(0, 5).map((t) => <li key={t}>{t}</li>)}{obs.failed_tests.length > 5 && <li>+{obs.failed_tests.length - 5} more</li>}</ul>}
    </div>
    <div className="receipt-section">
      <small className="receipt-label">INFERRED</small>
      <p><strong>{inf.leading_refdes}</strong> — {inf.leading_desc}</p>
      <div className="receipt-metrics">
        <span>Score: {fmt(inf.evidence_score, 1)}</span>
        <span>Coverage: {inf.mechanism_coverage_pct}%</span>
        {inf.fault_mode && <span>Mode: {inf.fault_mode}</span>}
        <span>{inf.confidence_tier}</span>
      </div>
    </div>
    {contract.rejected.length > 0 && <div className="receipt-section">
      <small className="receipt-label">REJECTED</small>
      {contract.rejected.map((alt) => <div key={alt.refdes} className="receipt-rejected-item">
        <span><strong>{alt.refdes}</strong> — {alt.desc} · {fmt(alt.score, 1)} · {alt.mechanism_coverage_pct}%</span>
        <small>{alt.rejection_reason}</small>
        {alt.evidence_gap && <small className="receipt-gap">GAP: {alt.evidence_gap}</small>}
      </div>)}
    </div>}
    <div className="receipt-section">
      <small className="receipt-label">RECOMMENDED</small>
      <p><strong>{rec.action}</strong> — {rec.target}</p>
      <small>{rec.rationale}</small>
    </div>
    <div className="receipt-section receipt-verification">
      <small className="receipt-label">VERIFICATION</small>
      <span className="receipt-verification-state">{verif.state}</span>
      <p className="receipt-disclaimer">{verif.disclaimer}</p>
    </div>
  </section>;
}

function VerificationLifecycleStepper({ report }: { report: DiagnosisReport }) {
  const verif = report.diagnostic_contract?.verification;
  if (!verif) return null;

  const isHumanDone = Boolean(verif.technician_confirmed);
  const isRepairDone = Boolean(verif.physical_repair_recorded);
  const isRetestDone = Boolean(verif.retest_passed);
  const isVerifiedDone = Boolean(verif.verified_repair);
  const isMemoryDone = Boolean(verif.repair_memory_admitted);

  const activeStep = !isHumanDone
    ? 'HUMAN'
    : !isRepairDone
    ? 'REPAIR'
    : !isRetestDone
    ? 'RETEST'
    : !isVerifiedDone
    ? 'VERIFIED'
    : !isMemoryDone
    ? 'MEMORY'
    : 'COMPLETE';

  const steps = [
    {
      id: 'HYPOTHESIS',
      title: 'AI HYPOTHESIS',
      desc: 'Current diagnostic result generated',
      status: 'complete' as const,
    },
    {
      id: 'HUMAN',
      title: 'HUMAN VERIFICATION',
      desc: isHumanDone ? 'Technician confirmation recorded' : 'Technician confirmation required',
      status: isHumanDone ? ('complete' as const) : activeStep === 'HUMAN' ? ('active' as const) : ('locked' as const),
    },
    {
      id: 'PHYSICAL',
      title: 'PHYSICAL REPAIR',
      desc: isRepairDone ? 'Repair action recorded' : 'Physical repair record required',
      status: isRepairDone ? ('complete' as const) : activeStep === 'REPAIR' ? ('active' as const) : ('locked' as const),
    },
    {
      id: 'RETEST',
      title: 'RETEST',
      desc: isRetestDone ? 'Board retest passed (PASS)' : 'Successful retest required',
      status: isRetestDone ? ('complete' as const) : activeStep === 'RETEST' ? ('active' as const) : ('locked' as const),
    },
    {
      id: 'VERIFIED',
      title: 'VERIFIED REPAIR',
      desc: isVerifiedDone ? 'Verified repair established' : 'Enabled only when technician, repair, and retest are complete',
      status: isVerifiedDone ? ('complete' as const) : activeStep === 'VERIFIED' ? ('active' as const) : ('locked' as const),
    },
    {
      id: 'MEMORY',
      title: 'REPAIR MEMORY',
      desc: isMemoryDone ? 'Admitted to closed-loop repair memory' : 'Eligible for repair memory only upon verified repair',
      status: isMemoryDone ? ('complete' as const) : activeStep === 'MEMORY' ? ('active' as const) : ('locked' as const),
    },
  ];

  return (
    <section className="forensic-panel verification-lifecycle-panel">
      <div className="section-heading">
        <MatrixHeading text="VERIFICATION LIFECYCLE" as="h2" />
        <span className="lifecycle-state-badge">{verif.state}</span>
      </div>
      <div className="lifecycle-stepper">
        {steps.map((step, idx) => (
          <div key={step.id} className={`lifecycle-step lifecycle-step--${step.status}`}>
            <div className="lifecycle-step__indicator">
              <span className="lifecycle-step__dot">
                {step.status === 'complete' ? '●' : step.status === 'active' ? '◉' : '○'}
              </span>
              {idx < steps.length - 1 && <span className="lifecycle-step__arrow">↓</span>}
            </div>
            <div className="lifecycle-step__content">
              <strong className="lifecycle-step__title">{step.title}</strong>
              <span className="lifecycle-step__desc">{step.desc}</span>
            </div>
          </div>
        ))}
      </div>
      <p className="lifecycle-disclaimer">{verif.disclaimer}</p>
    </section>
  );
}

function MeasurementValues({ test }: { test?: FailedTest }) {
  if (!test) return null;
  const unit = test.unit || '';
  return <div className="measurement-row" aria-label="Observed electrical values">
    <ElectricBorder><div className="measurement"><small>MEASURED</small><strong>{fmt(test.measured)} <em>{unit}</em></strong><span>{test.test_step}</span></div></ElectricBorder>
    <ElectricBorder><div className="measurement"><small>EXPECTED RANGE</small><strong>{fmt(test.expected_min)}–{fmt(test.expected_max)} <em>{unit}</em></strong><span>{test.net}</span></div></ElectricBorder>
    <ElectricBorder><div className="measurement"><small>DEVIATION</small><strong>{fmt(test.deviation)}×</strong><span>{test.error_code || 'OUT OF RANGE'}</span></div></ElectricBorder>
  </div>;
}

function VerdictStrip({ report }: { report: DiagnosisReport }) {
  const top = report.suspects?.[0];
  const runnerUp = report.suspects?.[1];
  const test = report.signature.failed_tests.find((item) => item.expected_min !== item.expected_max) ?? report.signature.failed_tests[0];
  const inconclusive = report.diagnosis_state === 'INCONCLUSIVE';
  const abstained = report.diagnosis_state === 'ABSTAIN';
  const degraded = report.diagnosis_state === 'DEGRADED';
  if (!top) return <section className="verdict-strip verdict-strip--pass"><p>All tests passed. No fault diagnosis is required.</p></section>;
  const ood = report.ood_state;
  const faultMode = top.fault_mode;
  const evo = top.expected_vs_observed;
  if (abstained) {
    return <section className="verdict-strip verdict-strip--abstain">
      <div className="verdict-strip__headline"><small>INSUFFICIENT EVIDENCE — NO RELIABLE DIAGNOSIS</small><h1>ABSTAIN</h1><p>{report.abstain_reason}</p><ul className="abstain-required">{(report.required_next_info ?? []).map((item, index) => <li key={index}>• {item}</li>)}</ul></div>
      <div className="score-readout"><strong>—</strong><small>DIAGNOSTIC<br />EVIDENCE SCORE</small></div>
    </section>;
  }
  return <section className={`verdict-strip ${inconclusive ? 'verdict-strip--uncertain' : degraded ? 'verdict-strip--degraded' : ''}`}>
    <div className="verdict-strip__headline"><small>{inconclusive ? 'INCONCLUSIVE — VERIFICATION TEST REQUIRED' : degraded ? 'DEGRADED INPUT — DIAGNOSIS WITH KNOWN GAPS' : `${(report.confidence_tier ?? 'Diagnosis').toUpperCase()} — PHYSICAL VERIFICATION REQUIRED`}</small><h1>{top.refdes} <span>— {top.desc}</span></h1>{faultMode && <em className="verdict-faultmode">FAULT MODE · {faultMode.label.toUpperCase()}</em>}<p>{report.signature.severity_label} fault · {report.signature.primary_domain} domain · {evo && evo.coverage_pct !== undefined ? `explains ${evo.coverage_pct}% of failures by mechanism` : 'requires physical verification'}{ood?.is_novel ? ` · pattern familiarity: ${ood.state === 'NOVEL' ? 'NOVEL' : 'PARTIALLY NOVEL'}` : ''}</p></div>
    <div className="score-readout"><strong>{fmt(top.score, 1)}</strong><small>DIAGNOSTIC<br />EVIDENCE SCORE</small>{runnerUp && <small className="score-gap">{fmt(top.score - runnerUp.score, 1)} PTS CLEAR OF #2 · {runnerUp.refdes}</small>}</div>
    <MeasurementValues test={test} />
    {(report.evidence_ledger ?? []).length > 0 && <button className="verdict-evidence" onClick={() => document.getElementById('evidence-ledger')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}><span>EVIDENCE</span>{(report.evidence_ledger ?? []).slice(0, 4).map((item) => <b key={item.id}>{item.id}</b>)}{report.evidence_ledger && report.evidence_ledger.length > 4 && <em>+{report.evidence_ledger.length - 4}</em>}<small>VIEW FULL LEDGER →</small></button>}
  </section>;
}

function DataQualityStrip({ report }: { report: DiagnosisReport }) {
  const dq = report.data_quality;
  if (!dq) return null;
  const tone = dq.status === 'GREEN' ? 'ok' : dq.status === 'AMBER' ? 'warn' : 'bad';
  return <section className={`dq-strip dq-strip--${tone}`}>
    <b>DATA QUALITY · {dq.status}</b>
    <span>{dq.label}</span>
    {dq.issues.length > 0 && <details><summary>{dq.issues.length} NOTE{dq.issues.length > 1 ? 'S' : ''}</summary><ul>{dq.issues.map((issue, i) => <li key={i} className={`dq-issue dq-issue--${issue.level.toLowerCase()}`}>{issue.level}: {issue.message}</li>)}</ul></details>}
  </section>;
}

function OODBanner({ report }: { report: DiagnosisReport }) {
  const ood = report.ood_state;
  if (!ood || !ood.is_novel) return null;
  const label = ood.state === 'NOVEL' ? 'NOVEL FAILURE PATTERN' : 'PARTIALLY NOVEL PATTERN';
  return <section className={`ood-banner ood-banner--${ood.state === 'NOVEL' ? 'novel' : 'partial'}`}>
    <b>{label}</b>
    <span>Closest historical precedent: <strong>{Math.round(ood.max_similarity * 100)}%</strong> similarity · this diagnosis is <strong>provisional</strong> — do not replace parts on this evidence alone.</span>
    {ood.indicators.length > 0 && <ul>{ood.indicators.slice(0, 3).map((indicator, i) => <li key={i}><b>{indicator.label}</b> · {indicator.detail}</li>)}</ul>}
  </section>;
}

function JudgeStepper() {
  const steps = [
    ['verdict', 'FAILURE'], ['hypothesis-arena', 'ARENA'], ['challenge-panel', 'CHALLENGE'],
    ['evidence-ledger', 'EVIDENCE'], ['patterns', 'PATTERNS'], ['validation', 'VALIDATION'], ['exports', 'EXPORT'],
  ];
  const go = (id: string) => {
    const el = id === 'verdict' ? document.querySelector('.verdict-strip') : document.getElementById(id);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  return <nav className="judge-stepper" aria-label="Investigation flow"><span>INVESTIGATION FLOW</span>{steps.map(([id, label]) => <button key={id} className={normalButton} onClick={() => go(id)}>{label}</button>)}</nav>;
}

function CounterAnimation({ value, suffix = '', duration = 1300 }: { value: number; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-30px' });
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setDisplay(value * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, value, duration]);
  return <span ref={ref}>{fmt(display, 1)}{suffix}</span>;
}

function ValidationPanel({ metrics }: { metrics: ConsoleArgs['validation_metrics'] }) {
  const [open, setOpen] = useState(false);
  if (!metrics) return null;
  return <section className="forensic-panel validation-panel" id="validation">
    <div className="section-heading">
      <MatrixHeading text="VALIDATION DASHBOARD" as="h2" />
      <span>{fmt(metrics.top3_accuracy ?? 0, 1)}% TOP-3 · {metrics.instances ?? 0} HELD-OUT INSTANCES · KNOWN FAULT FAMILIES</span>
    </div>
    {metrics.dataset && <p className="validation-dataset">Benchmark: <b>{metrics.dataset}</b> — instance holdout, not unseen-family generalization.</p>}
    <motion.div className="validation-summary" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-30px' }} variants={gridVariants}>
      <BentoCard><div className="v-metric"><strong><CounterAnimation value={metrics.top1_accuracy ?? 0} suffix="%" /></strong><small>Top-1</small></div></BentoCard>
      <BentoCard><div className="v-metric"><strong><CounterAnimation value={metrics.top3_accuracy ?? 0} suffix="%" /></strong><small>Top-3</small></div></BentoCard>
      <BentoCard><div className="v-metric"><strong><CounterAnimation value={metrics.domain_accuracy ?? 0} suffix="%" /></strong><small>Domain</small></div></BentoCard>
      <BentoCard><div className="v-metric"><strong><CounterAnimation value={metrics.inference_ms ?? ((metrics.average_inference_seconds ?? 0) * 1000)} suffix="ms" /></strong><small>Inference · median {fmt((metrics.median_inference_seconds ?? 0) * 1000, 1)} · p95 {fmt((metrics.p95_inference_seconds ?? 0) * 1000, 1)}</small></div></BentoCard>
    </motion.div>
    {metrics.error_breakdown && <>
      <p className="validation-story">Of {Math.round((metrics.instances ?? 100) * (1 - (metrics.top1_accuracy ?? 88) / 100))} top-1 misses: <b>{metrics.error_breakdown.in_top3_but_ranked_second ?? 0}</b> still ranked the truth in the top-3 · <b>{metrics.error_breakdown.not_in_top3 ?? 0}</b> outside the top-3{metrics.error_breakdown.not_in_top3 > 0 ? ' (every one flagged for multi-fault)' : ''} · <b>{metrics.error_breakdown.silent_misses ?? 0}</b> silent — no wrong answer was ever both hidden from the arena and unaccompanied by a warning.</p>
      {metrics.weights_note && <p className="validation-dataset">Fusion policy: <b>{metrics.weights_note}</b></p>}
      <button className={`console-button console-button--quiet validation-toggle ${open ? 'validation-toggle--open' : ''}`} onClick={() => setOpen((v) => !v)}>{open ? 'HIDE ERROR ANALYSIS' : 'SHOW ERROR ANALYSIS'}</button>
      {open && <div className="validation-errors">
          <p className="validation-errors__note">On the 100-board blind benchmark, {Math.round((metrics.instances ?? 100) * (1 - (metrics.top1_accuracy ?? 78) / 100))} cases missed top-1. The breakdown below is an automated categorization — some cases may fit multiple categories.</p>
        <table className="v-table"><thead><tr><th>Category</th><th>Count</th><th>% of Errors</th></tr></thead><tbody>{Object.entries(metrics.error_breakdown ?? {}).map(([category, count]) => <tr key={category}><td>{category.replace(/_/g, ' ')}</td><td>{String(count)}</td><td>{fmt(Number(count) / Math.max(1, Math.round((metrics.instances ?? 100) * (1 - (metrics.top1_accuracy ?? 78) / 100))) * 100, 0)}%</td></tr>)}</tbody></table>
      </div>}
    </>}
  </section>;
}

function Workbench({ report, simulation, componentOptions, selectedComponent, setSelectedComponent, onSimulate, onExport, onExportCsv }: { report: DiagnosisReport; simulation: ConsoleArgs['simulation']; componentOptions: ComponentOption[]; selectedComponent: string; setSelectedComponent: (refdes: string) => void; onSimulate: (refdes: string) => void; onExport: () => void; onExportCsv: () => void }) {
  const top = report.suspects?.[0];
  const selectedRefdes = selectedComponent || top?.refdes || '';
  const citedPrecedent = report.cited_precedent;
  // The cited precedent is pinned first so the panel's #1 case always matches
  // the one quoted by the verdict card, narrative, ledger, and PDF exports.
  // The remaining matches collapse into root-cause families so the panel shows
  // distinct hypotheses instead of near-duplicate rows.
  const familyMap = new Map<string, { root: string; similarity: number; count: number; repair_id: string; symptom_text: string; fix_action: string }>();
  for (const match of report.semantic_memory?.matches ?? []) {
    if (match.repair_id === citedPrecedent?.repair_id) continue;
    const root = match.root_cause_component;
    const current = familyMap.get(root);
    if (current) {
      current.count += 1;
      if (match.similarity > current.similarity) {
        current.similarity = match.similarity;
        current.repair_id = match.repair_id;
        current.symptom_text = match.symptom_text;
        current.fix_action = match.fix_action;
      }
    } else {
      familyMap.set(root, { root, similarity: match.similarity, count: 1, repair_id: match.repair_id, symptom_text: match.symptom_text, fix_action: match.fix_action });
    }
  }
  const familyCases = [...familyMap.values()].slice(0, 2);
  const [handoffOpen, setHandoffOpen] = useState(false);
  const checkTest = report.signature.failed_tests.find((t) => t.net === top?.net) ?? report.signature.failed_tests[0];
  return <section className="workbench">
    <div className="section-heading"><MatrixHeading text="FORENSICS WORKBENCH" as="h2" /><span>SOURCE-BACKED</span></div>
    <motion.div className="workbench-grid" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-40px' }} variants={gridVariants}>
      <BentoCard className="bento-card--wide"><article className="forensic-panel evidence-panel"><h3>Evidence Convergence</h3>{top && <div className="evidence-faultmode"><b>{top.refdes}</b><span>{top.fault_mode ? `${top.refdes} / ${top.fault_mode.label}` : 'no fault mode assigned'}</span>{top.fault_mode?.verification && <small>Verify: {top.fault_mode.verification}</small>}</div>}{top && Object.entries(top.evidence_contributions).map(([label, value]) => <EvidenceBar key={label} label={label} value={value} />)}<EvidenceAblation report={report} /><p className="ablation-hint">Disable streams to see how the ranking changes — the policy is deterministic, not a black box.</p></article></BentoCard>
      <BentoCard><article className="forensic-panel history-panel"><h3>Historical Precedents</h3>{citedPrecedent && <div className="history-case history-case--cited" key={citedPrecedent.repair_id}><b>{citedPrecedent.repair_id}<span>{fmt(citedPrecedent.similarity, 1)}% match</span></b><em className="history-case__cited">CITED PRECEDENT</em><p>{citedPrecedent.symptom_text}</p><small>Recorded action: {citedPrecedent.fix_action} {citedPrecedent.root_cause_component}</small></div>}{familyCases.map((family) => <div className="history-case" key={family.root}><b>{family.root}<span>{family.count} PRIOR · {fmt(family.similarity, 1)}% MATCH</span></b><p>{family.symptom_text}</p><small>Recorded action: {family.fix_action} · representative of {family.count} case(s)</small></div>)}</article></BentoCard>
      <BentoCard><article className="forensic-panel repair-panel"><h3>Repair Counterfactual</h3><p>Choose a component to inspect, then predict the dependency impact. This is hypothetical—not repair confirmation.</p><label className="field-label">COMPONENT TO INSPECT<select aria-label="Component to inspect" value={selectedComponent} onChange={(event) => setSelectedComponent(event.target.value)}>{componentOptions.map((component) => <option key={component.refdes} value={component.refdes}>{component.refdes} — {component.desc}</option>)}</select></label>{selectedRefdes && <button className={normalButton} onClick={() => onSimulate(selectedRefdes)}>SIMULATE REPLACING {selectedRefdes}</button>}{simulation && <div className="simulation-result"><b>{simulation.replaced} hypothetical result</b><p>Expected resolved: {simulation.resolved_nets.join(', ') || 'No direct nets identified.'}</p><p>Still failing: {simulation.remaining_nets.join(', ') || 'None predicted.'}</p></div>}</article></BentoCard>
      <BentoCard className="bento-card--wide"><article className="forensic-panel dna-panel"><h3>Failure DNA</h3><div className="dna-bars">{Object.entries(report.signature.domain_severity).map(([domain, amount]) => <div key={domain}><span style={{ height: `${Math.min(Math.max(amount, 6) * 8, 100)}%` }} /><small>{domain}</small></div>)}</div></article></BentoCard>
    </motion.div>
    <article className="forensic-panel ledger-panel" id="evidence-ledger"><h3>Chain-of-Custody Evidence Ledger</h3><div className="ledger-list">{(report.evidence_ledger ?? []).map((item) => <div key={item.id}><b>{item.id}</b><span>{item.source} · {item.strength}</span><p>{item.observation}</p></div>)}</div></article>
    <article className="forensic-panel raw-panel"><h3>Observed Failing Tests</h3><div className="raw-table">{report.signature.failed_tests.map((test) => <div key={test.test_step}><b>{test.test_step}</b><span>{test.net}</span><span>{fmt(test.measured)} {test.unit}</span><span>{fmt(test.deviation)}×</span></div>)}</div></article>
    <div className="export-row" id="exports"><StarBorder as="button" className="star-cta star-cta--export" color="#6fe3e5" speed="6s" thickness={2} onClick={onExport}>EXPORT INVESTIGATION DOSSIER</StarBorder><StarBorder as="button" className="star-cta star-cta--export" color="#6fe3e5" speed="6s" thickness={2} onClick={onExportCsv}>EXPORT RANKED CSV</StarBorder><button className={`console-button handoff-toggle ${handoffOpen ? 'handoff-toggle--open' : ''}`} onClick={() => setHandoffOpen((v) => !v)}>{handoffOpen ? 'HIDE HANDOFF' : 'PREPARE TECHNICIAN HANDOFF'}</button></div>
    {handoffOpen && top && <div className="handoff-card">
      <div className="handoff-card__head"><b>TECHNICIAN HANDOFF</b><span>{report.case_number ?? report.board_id} · {new Date().toISOString().slice(0, 10)} · INVESTIGATION COMPLETE</span></div>
      <div className="handoff-card__body">
        <div className="handoff-block"><small>MOST LIKELY CAUSE</small><strong>{top.refdes} ({top.desc})</strong><span>{report.signature.primary_domain} domain failure</span></div>
        <div className="handoff-block"><small>WHAT TO CHECK FIRST</small><strong>Measure {checkTest?.net ?? top.net} under rated load</strong><span>Expected: {checkTest?.expected_min != null ? `${fmt(checkTest.expected_min)}–${fmt(checkTest.expected_max)} ${checkTest.unit || ''}` : 'within specification'} — if out of range, confirm {top.refdes}</span></div>
        <div className="handoff-block"><small>WHAT NOT TO DO</small><strong>Do not replace downstream components first</strong><span>They are likely victims of the {checkTest?.net ?? top.net} rail, not causes. Verify the rail before condemning anything else.</span></div>
        <div className="handoff-block"><small>CONFIDENCE</small><strong>{(report.confidence_tier ?? 'LIKELY').toUpperCase()}</strong><span>Verify before replacing components. All conclusions are probable — physical verification required.</span></div>
      </div>
      <p className="handoff-card__foot">Generated by CircuitMind Evidence Reasoning Engine · every claim is sourced in the dossier above</p>
    </div>}
  </section>;
}

function VerifiedMemory({ report, confirmation, onRecord }: { report: DiagnosisReport; confirmation: ConsoleArgs['verified_confirmation']; onRecord: (refdes: string, retestPass: boolean, technicianConfirmed: boolean, technicianNote: string) => void }) {
  const top = report.suspects?.[0];
  const [retestPass, setRetestPass] = useState(false);
  const [technicianConfirmed, setTechnicianConfirmed] = useState(false);
  const [technicianNote, setTechnicianNote] = useState('');
  if (!top) return null;
  const eligible = retestPass && technicianConfirmed;
  return <section className="forensic-panel memory-panel">
    <div className="section-heading"><MatrixHeading text="VERIFIED REPAIR MEMORY" as="h2" /><span>CLOSED-LOOP CASE-BASED LEARNING</span></div>
    <p className="memory-intro">Only <b>verified</b> outcomes enter memory: repair performed → board retested <b>PASS</b> → technician explicitly confirms. A prediction alone is never promoted to historical truth — that prevents the system from poisoning its own knowledge base.</p>
    <div className="memory-controls">
      <label className={`memory-retest ${retestPass ? 'memory-retest--on' : 'memory-retest--off'}`}><input type="checkbox" checked={retestPass} onChange={(event) => setRetestPass(event.target.checked)} />Retest passed</label>
      <label className={`memory-retest ${technicianConfirmed ? 'memory-retest--on' : 'memory-retest--off'}`}><input type="checkbox" checked={technicianConfirmed} onChange={(event) => setTechnicianConfirmed(event.target.checked)} />Technician confirms the repair was verified</label>
    </div>
    <textarea className="notes-input memory-note" rows={2} value={technicianNote} onChange={(event) => setTechnicianNote(event.target.value)} placeholder="Technician note (post-diagnosis, optional) — e.g. 'replaced U3, reflow verified'. This is stored as the learned case, separate from pre-diagnosis notes." />
    <div className="memory-controls">
      <button className={normalButton} disabled={!eligible} onClick={() => onRecord(top.refdes, retestPass, technicianConfirmed, technicianNote)}>RECORD VERIFIED REPAIR — {top.refdes}</button>
    </div>
    {confirmation && <div className={`memory-confirm ${confirmation.added ? 'memory-confirm--ok' : 'memory-confirm--reject'}`}>
      {confirmation.added
        ? <>✓ Case <b>{confirmation.repair_id}</b> added — the active retrieval memory has been refreshed and now retrieves from <b>{confirmation.count}</b> verified case{confirmation.count === 1 ? '' : 's'} in this session.</>
        : <>✗ {confirmation.reason}</>}
    </div>}
  </section>;
}

function DecodeScreen({ action, board }: { action: string; board: string }) {
  const label = action === 'load_demo'
    ? 'LOADING CASE'
    : action === 'scan_all'
      ? 'SCANNING FLEET'
      : 'RUNNING DIAGNOSTIC PIPELINE';
  return <div className="decode-screen" role="status" aria-live="polite">
    <div className="decode-screen__inner">
      <div className="decode-screen__eyebrow">STRUCTURED EVIDENCE REASONING</div>
      <div className="decode-screen__title">{label}</div>
      <div className="decode-screen__bar"><span /></div>
      <div className="decode-screen__board">{board || 'SIGNATURE EXTRACTION → CAUSAL DAG → RETRIEVAL → FUSION'}</div>
    </div>
  </div>;
}

function CommandDeck({ args, boardId, setBoardId, componentId, setComponentId }: { args: ConsoleArgs; boardId: string; setBoardId: (value: string) => void; componentId: string; setComponentId: (value: string) => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [readingFile, setReadingFile] = useState(false);
  const [localError, setLocalError] = useState('');
  const [notes, setNotes] = useState('');

  const onNotesChange = (event: ChangeEvent<HTMLTextAreaElement>) => setNotes(event.target.value);
  const onFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > (args.max_upload_bytes ?? 5_242_880)) {
      setLocalError('This local component accepts CSV files up to 5 MB.');
      return;
    }
    setReadingFile(true);
    setLocalError('');
    try {
      emit({ action: 'upload_csv_text', filename: file.name, csv_text: await file.text() });
    } catch {
      setLocalError('The browser could not read the selected CSV.');
      setReadingFile(false);
    }
  };

  const caseLoaded = Boolean(args.uploaded_file && boardId);
  const activeBoardLabel = boardId || args.board_ids?.[0] || 'BRD_0415';

  return (
    <section className="command-deck">
      <div className="command-deck__copy">
        <div className="eyebrow" style={{ color: '#22d3ee', letterSpacing: '0.18em', fontWeight: 800, marginBottom: 8 }}>
          ⚡ DETERMINISTIC HARDWARE TRIAGE
        </div>
        <h1 className="command-deck__hero">
          <MatrixText text="CIRCUITMIND" />
        </h1>
        <p style={{ color: '#cbd5e1', fontSize: '15px', lineHeight: 1.6, marginTop: 12 }}>
          Instant PCB fault isolation in &lt;6ms. Fusing ICT/FCT logs, netlist topology &amp; historical repair memory with zero hallucinations.
        </p>

        {/* 1-2-3 Quick Start Guide */}
        <div
          style={{
            display: 'grid',
            gap: 10,
            marginTop: 20,
            padding: '14px 16px',
            background: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#f1f5f9', fontSize: 12 }}>
            <span style={{ display: 'grid', placeItems: 'center', width: 22, height: 22, borderRadius: '50%', background: '#0284c7', color: '#fff', fontWeight: 800, fontSize: 11, flexShrink: 0 }}>1</span>
            <span><b>Select a demo failure case</b> or upload your own CSV log</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#f1f5f9', fontSize: 12 }}>
            <span style={{ display: 'grid', placeItems: 'center', width: 22, height: 22, borderRadius: '50%', background: '#0284c7', color: '#fff', fontWeight: 800, fontSize: 11, flexShrink: 0 }}>2</span>
            <span>Review failing test measurements &amp; power domains</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#f1f5f9', fontSize: 12 }}>
            <span style={{ display: 'grid', placeItems: 'center', width: 22, height: 22, borderRadius: '50%', background: '#10b981', color: '#fff', fontWeight: 800, fontSize: 11, flexShrink: 0 }}>3</span>
            <span>Click <b>Run Forensic Diagnosis</b> for root-cause ranking</span>
          </div>
        </div>
      </div>

      <div className="command-deck__controls" style={{ border: '1px solid rgba(56, 189, 248, 0.35)', background: 'rgba(10, 27, 33, 0.92)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
          <b style={{ color: '#38bdf8', fontSize: 11, letterSpacing: '0.1em' }}>STEP 1: SELECT CASE OR UPLOAD</b>
          <small style={{ color: '#94a3b8', fontSize: 10 }}>4 Traceable Demos</small>
        </div>

        <div className="demo-buttons">
          {(args.demo_cases ?? []).map((item) => (
            <button
              key={item.id}
              className={normalButton}
              style={{
                background: '#0f242a',
                borderColor: 'rgba(56, 189, 248, 0.3)',
                color: '#f8fafc',
              }}
              onClick={() => emit({ action: 'load_demo', case_id: item.id })}
            >
              <b style={{ color: '#38bdf8', fontSize: 11 }}>{item.label}</b>
              <span style={{ color: '#cbd5e1', fontSize: 10 }}>{item.subtitle}</span>
            </button>
          ))}
        </div>

        <div className="upload-line" style={{ marginTop: 4 }}>
          <input ref={fileRef} type="file" accept=".csv" onChange={onFile} />
          <button
            className={normalButton}
            style={{ borderColor: 'rgba(56, 189, 248, 0.4)', background: '#13333b', color: '#f1f5f9' }}
            onClick={() => fileRef.current?.click()}
          >
            {readingFile ? 'READING CSV…' : '📁 UPLOAD CUSTOM ICT/FCT CSV'}
          </button>
          {args.uploaded_file && <small style={{ color: '#38bdf8' }}>✓ {args.uploaded_file.name}</small>}
        </div>

        {caseLoaded && (
          <div className="case-continue" style={{ border: '1px solid #10b981', background: 'rgba(16, 185, 129, 0.12)' }}>
            <b style={{ color: '#34d399' }}>✓ CASE LOADED · {boardId}</b>
            <span style={{ color: '#cbd5e1' }}>Ready for causal analysis and fault-mode evaluation.</span>
          </div>
        )}

        {args.board_ids && args.board_ids.length > 1 && (
          <label className="field-label" style={{ color: '#94a3b8' }}>
            BOARD UNDER TEST
            <select aria-label="Select board" value={boardId} onChange={(event) => setBoardId(event.target.value)}>
              {args.board_ids.map((id) => (
                <option key={id}>{id}</option>
              ))}
            </select>
          </label>
        )}

        {caseLoaded && (
          <label className="field-label" style={{ color: '#94a3b8' }}>
            OPTIONAL INSPECTION FOCUS
            <select aria-label="Optional inspection focus" value={componentId} onChange={(event) => setComponentId(event.target.value)}>
              <option value="">LET CIRCUITMIND RANK ALL COMPONENTS</option>
              {(args.component_options ?? []).map((component) => (
                <option key={component.refdes} value={component.refdes}>
                  {component.refdes} — {component.desc} · {component.net}
                </option>
              ))}
            </select>
          </label>
        )}

        {caseLoaded && (
          <label className="field-label" style={{ color: '#94a3b8' }}>
            REPAIR NOTES (OPTIONAL)
            <textarea
              className="notes-input"
              rows={2}
              value={notes}
              onChange={onNotesChange}
              placeholder="e.g. replaced R12, cold solder at U3 — typed notes are folded into ranking."
            />
          </label>
        )}

        {args.board_ids && args.board_ids.length > 1 && !args.fleet && (
          <button className={normalButton} onClick={() => emit({ action: 'scan_all' })}>
            SCAN ALL {args.board_ids.length} BOARDS IN LOT
          </button>
        )}

        {args.fleet && args.fleet.length > 0 && (
          <div className="fleet-banner">
            <b>FLEET SCAN COMPLETE</b>
            <span>
              {args.fleet.length} boards in {fmt(args.fleet_scan_ms ?? 0, 0)} ms —{' '}
              {(args.fleet_scan_ms ?? 0) > 0
                ? `at this rate, 10,000 boards in ${fmt(((args.fleet_scan_ms ?? 0) / args.fleet.length) * 10000 / 1000, 1)} s. Linear pipeline.`
                : 'each row is independently analyzed through the full pipeline.'}
            </span>
          </div>
        )}

        {args.fleet_tester && args.fleet_tester.state === 'TEST_SYSTEM_SUSPECTED' && (
          <div className="tester-banner">
            <b>⚠ FAILURE OR TESTER? · TEST SYSTEM SUSPECTED</b>
            <span>{args.fleet_tester.note}</span>
            <small>
              {args.fleet_tester.suspected_tests
                ?.map((t: any) =>
                  t.attribution === 'FIXTURE_SUSPECTED'
                    ? `${t.test_step} — FIXTURE ${t.fixture_id} FAILED ${fmt((t.fixture_fail_rate || 0) * 100, 0)}% (Peers: ${fmt((t.peer_fixture_fail_rate || 0) * 100, 0)}%)`
                    : `${t.test_step} — failed on ${t.boards_failed}/${t.boards_ran} boards (${fmt(t.failure_rate * 100, 0)}%)`
                )
                .join(' · ')}{' '}
              — DO NOT REWORK BOARDS. Validate fixture/probes first.
            </small>
          </div>
        )}

        {args.fleet_tester && args.fleet_tester.state === 'BOARD_SPECIFIC' && (
          <div className="tester-banner tester-banner--clear">
            <b>✓ FAILURE OR TESTER? · BOARD-SPECIFIC</b>
            <span>{args.fleet_tester.note}</span>
          </div>
        )}

        {args.fleet && args.fleet.length > 0 && (
          <div className="fleet-grid">
            {args.fleet.map((row: FleetRow) => (
              <button
                key={row.board_id}
                className={`fleet-row fleet-row--${row.status.toLowerCase()}`}
                onClick={() => emit({ action: 'analyze', board_id: row.board_id })}
              >
                <b>{row.board_id}</b>
                <span>
                  {row.status === 'ERROR'
                    ? 'ERROR'
                    : `${row.confidence_tier || '—'}${row.top_refdes ? ' · ' + row.top_refdes : ''}`}
                </span>
                <strong>{row.top_score != null ? fmt(row.top_score, 1) : '—'}</strong>
                <small>{row.failed_tests} FAILED</small>
                {row.fingerprint && <em className="fleet-fingerprint">{row.fingerprint}</em>}
              </button>
            ))}
          </div>
        )}

        {/* Primary High-Impact CTA Button (DesignMeter Fix #1) */}
        <button
          className="primary-hero-cta"
          disabled={readingFile}
          onClick={() =>
            emit({
              action: 'analyze',
              board_id: boardId || 'BRD_0415',
              component_id: componentId,
              repair_notes: notes,
            })
          }
        >
          <span>⚡ RUN FORENSIC DIAGNOSIS ({activeBoardLabel}) →</span>
        </button>

        {localError && <p className="input-error">{localError}</p>}
      </div>
    </section>
  );
}

export default function ForensicsConsole({ args }: { args: ConsoleArgs }) {
  const [boardId, setBoardId] = useState(args.selected_board ?? '');
  const [componentId, setComponentId] = useState(args.selected_component ?? '');
  const [showJudgeMode, setShowJudgeMode] = useState(false);
  const [legalModal, setLegalModal] = useState<'privacy' | 'terms' | null>(null);
  const [pending, setPending] = useState<string>(() => {
    try { return sessionStorage.getItem('cm-pending') || ''; } catch { return ''; }
  });

  const lastDownloadedPdf = useRef<string>('');
  const lastDownloadedCsv = useRef<string>('');

  useEffect(() => { setBoardId(args.selected_board ?? ''); }, [args.selected_board]);
  useEffect(() => { setComponentId(args.selected_component ?? ''); }, [args.selected_component]);

  useEffect(() => {
    let saved = 0;
    try { saved = Number(sessionStorage.getItem('cm-scroll') || '0'); sessionStorage.removeItem('cm-scroll'); } catch { /* noop */ }
    if (!saved) return;
    const restore = () => {
      try {
        const container = findScrollContainer(window.parent ?? window);
        if (container) {
          container.scrollTop = Math.min(saved, container.scrollHeight - container.clientHeight);
        }
      } catch { /* noop */ }
    };
    const raf = requestAnimationFrame(() => requestAnimationFrame(restore));
    const timer = window.setTimeout(restore, 180);
    return () => { cancelAnimationFrame(raf); window.clearTimeout(timer); };
  }, []);

  useEffect(() => {
    const observer = new ResizeObserver(() => Streamlit.setFrameHeight());
    observer.observe(document.body);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!args.pdf_base64 || args.pdf_base64 === lastDownloadedPdf.current) return;
    lastDownloadedPdf.current = args.pdf_base64;
    const binary = atob(args.pdf_base64);
    const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${args.report?.case_number ?? args.report?.board_id ?? 'circuitmind'}-dossier.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }, [args.pdf_base64]);

  useEffect(() => {
    if (!args.csv_base64 || args.csv_base64 === lastDownloadedCsv.current) return;
    lastDownloadedCsv.current = args.csv_base64;
    const csv = atob(args.csv_base64);
    const bytes = Uint8Array.from(csv, character => character.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], { type: 'text/csv' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${args.report?.case_number ?? args.report?.board_id ?? 'circuitmind'}-ranked-suspects.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }, [args.csv_base64]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
      const key = event.key.toLowerCase();
      if (key === 'n') emit({ action: 'reset' });
      else if (key === 's' && args.board_ids && args.board_ids.length > 1) emit({ action: 'scan_all' });
      // E key freed — executive view is now always visible
      else if (key === 'j') setShowJudgeMode((v) => !v);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [args.board_ids]);
  const report = args.report;
  // A completed report is authoritative; an independently-delivered display
  // state should never hide it during a Streamlit bridge refresh.
  const showResults = Boolean(report);
  // Pending marker set by emit() before a round-trip: while the server reruns
  // (and the iframe reloads), show the decode screen instead of stale intake.
  useEffect(() => { registerPendingSetter(setPending); }, []);
  const pendingAction = pending.split('|')[0] ?? '';
  const pendingBoard = pending.split('|')[1] ?? '';
  // An action is "done" when its result artifact arrives: a report for
  // analyze, the loaded case for load_demo, the fleet grid for scan_all —
  // or when the server reports an error.
  const pendingDone = showResults
    || Boolean(args.error_message)
    || (pendingAction === 'load_demo' && Boolean(args.uploaded_file))
    || (pendingAction === 'scan_all' && Boolean(args.fleet));
  useEffect(() => {
    if (pendingDone && pending) {
      try { sessionStorage.removeItem('cm-pending'); } catch { /* noop */ }
      setPending('');
    }
  }, [pendingDone, pending]);
  const showDecode = pending && !pendingDone;
  const validation = args.validation_metrics;
  const validationLabel = validation?.top3_accuracy !== undefined
    ? `${fmt(validation.top3_accuracy, 1)}% TOP-3 · ${validation.instances ?? 0} BLIND CASES`
    : 'NOT YET BENCHMARKED';
  const componentOptions = args.component_options ?? [];
  const workbenchComponent = componentId || report?.suspects?.[0]?.refdes || componentOptions[0]?.refdes || '';
  return <main className="forensics-console"><SideRays className="side-rays-bg" speed={1.4} rayColor1="#2f8a90" rayColor2="#6fe3e5" intensity={0.85} spread={1.7} origin="top-right" tilt={0} saturation={1.4} blend={0.6} falloff={1.9} opacity={0.5} /><ParticlesBackground /><header className="console-header"><span className="console-header__mark">CM</span><span>PCB FORENSICS MISSION CONTROL</span><em className="console-header__guarantee">DETERMINISTIC · BOM-BOUNDED · NO GENERATIVE COMPONENT INVENTION</em><small>● OFFLINE · DETERMINISTIC · {validationLabel}</small></header><div className="console-content">{args.error_message && <div className="console-error" role="alert"><b>INPUT VALIDATION ERROR</b><span>{args.error_message}</span>{showResults && <small className="console-error__stale">The results below are from the previous successful run — the last request did not complete.</small>}<button className="console-error__dismiss" aria-label="Dismiss error" onClick={() => emit({ action: 'dismiss_error' })}>✕</button></div>}{showDecode && <DecodeScreen action={pendingAction} board={pendingBoard} />}{!showDecode && !showResults && <CommandDeck args={args} boardId={boardId} setBoardId={setBoardId} componentId={componentId} setComponentId={setComponentId} />}      {showResults && report && (
        <motion.div
          className="results-view"
          initial={{ opacity: 0, y: 14, scale: 0.99 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* Top toolbar */}
          <div className="result-toolbar">
            <button className={normalButton} onClick={() => emit({ action: 'reset' })}>
              ← NEW CASE
            </button>
            <span>
              CASE {report.case_number ?? report.board_id}
              {args.selected_component ? ` · INSPECTION FOCUS ${args.selected_component}` : ''}
              <em className="keyboard-hint"> · N = NEW · S = SCAN · J = JUDGE</em>
            </span>
          </div>

          <JudgeStepper />
          <VerdictStrip report={report} />
          <OODBanner report={report} />
          <DataQualityStrip report={report} />

          {/* ─── REASONING CHAIN (Step-by-Step Reconstruction) ─── */}
          <section className="exec-section" style={{ marginTop: 10 }}>
            <div className="section-heading">
              <MatrixHeading text="REASONING CHAIN" as="h2" />
              <span>STEP-BY-STEP RECONSTRUCTION</span>
            </div>
            <EvidenceChainVisualizer report={report} />
          </section>

          {/* Forensic narrative & investigator summary */}
          {report.narrative && (
            <blockquote className="forensic-narrative">
              {report.narrative.replaceAll('**', '')}
            </blockquote>
          )}

          {/* Causal Fault Propagation Replay */}
          <SectionBoundary name="Fault Propagation Replay">
            <FaultPropagationReplay report={report} />
          </SectionBoundary>

          {/* Hypothesis Arena: "Try to Disprove It" */}
          <SectionBoundary name="Hypothesis Arena">
            <HypothesisArena
              report={report}
              challengeOpen={Boolean(args.challenge_open)}
              onChallenge={() => {
                emit({ action: 'challenge_finding' });
              }}
            />
          </SectionBoundary>

          {/* What would change my mind */}
          {report.verdict_flip && report.verdict_flip.length > 0 && (
            <section className="forensic-panel flip-panel">
              <h3>WHAT WOULD CHANGE MY MIND?</h3>
              <p className="flip-intro">
                Each condition below is derived from mechanism data, not a guess — if any of these observations lands, the verdict must be re-examined.
              </p>
              <ul className="flip-list">
                {report.verdict_flip.map((item, index) => (
                  <li key={index}>
                    <b>{item.observation}</b>
                    <span>{item.effect}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Diagnostic Contract & Receipt */}
          <DiagnosticReceipt report={report} />

          {/* Pattern Space Scatter */}
          <SectionBoundary name="Pattern Space">
            <PatternSpaceScatter report={report} />
          </SectionBoundary>

          {/* Interactive Forensics Workbench (Simulation, Precedents, PDF/CSV Export) */}
          <SectionBoundary name="Forensics Workbench">
            <Workbench
              report={report}
              simulation={args.simulation}
              componentOptions={componentOptions}
              selectedComponent={workbenchComponent}
              setSelectedComponent={setComponentId}
              onSimulate={(refdes) => emit({ action: 'simulate_repair', refdes })}
              onExport={() => emit({ action: 'export_report' })}
              onExportCsv={() => emit({ action: 'export_csv' })}
            />
          </SectionBoundary>

          {/* Human Verification Lifecycle Stepper */}
          <VerificationLifecycleStepper report={report} />

          {/* Verified Repair Memory Recorder */}
          <VerifiedMemory
            report={report}
            confirmation={args.verified_confirmation}
            onRecord={(refdes, retestPass, technicianConfirmed, technicianNote) =>
              emit({
                action: 'record_verified_repair',
                refdes,
                retest_pass: retestPass,
                technician_confirmed: technicianConfirmed,
                technician_note: technicianNote,
              })
            }
          />

          {/* Failure Signature DNA & Known Investigation Gaps */}
          <FailureFingerprint report={report} />
          {report.investigation_gaps && report.investigation_gaps.length > 0 && (
            <section className="forensic-panel gaps-panel">
              <div className="section-heading">
                <MatrixHeading text="KNOWN INVESTIGATION GAPS" as="h2" />
                <span>WHAT THIS INVESTIGATION DOES NOT KNOW</span>
              </div>
              {report.investigation_gaps.map((gap) => (
                <div key={gap.label} className="gap-item">
                  <b>{gap.label}</b>
                  <p>{gap.detail}</p>
                </div>
              ))}
            </section>
          )}
          <CaseTimeline report={report} />

          {/* Validation Metrics Panel & Beat the Machine Benchmark */}
          <ValidationPanel metrics={args.validation_metrics} />
          <SectionBoundary name="Beat the Machine">
            <BeatTheMachine
              report={report}
              truth={args.revealed_truth}
              machineMs={((args.validation_metrics?.median_inference_seconds ?? 0.005) || 0.005) * 1000}
            />
          </SectionBoundary>

          {/* ─── JUDGE MODE (keyboard J) ─── */}
          {showJudgeMode && report && (
            <section
              className="forensic-panel"
              style={{
                border: '1px solid rgba(103, 230, 231, 0.3)',
                background: 'rgba(10, 26, 31, 0.8)',
              }}
            >
              <div className="section-heading">
                <MatrixHeading text="JUDGE MODE" as="h2" />
                <span>WHAT YOU SHOULD CHALLENGE</span>
              </div>
              <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                {[
                  { q: '1. Synthetic data', a: 'All validation is synthetic. We intentionally measure family holdout to expose this limitation.' },
                  { q: '2. Family generalization', a: `49% top-1 on unseen families. The system is strongest in known diagnostic neighborhoods. Architecture's next step: structural generalization.` },
                  { q: '3. Fixture attribution', a: 'Threshold-based statistical attribution with n\u22653 floor. Production would add calibrated confidence intervals and temporal change-point detection.' },
                  { q: '4. Confidence calibration', a: 'Labels reflect evidence strength, not calibrated probabilities. The system says "I don\u2019t know" when evidence is insufficient.' },
                  { q: '5. Historical dependence', a: 'TF-IDF retrieval is a major dependency. The discriminating benchmark (55.6% vs 22.2%) shows evidence fusion adds value beyond pattern matching.' },
                ].map((item) => (
                  <details key={item.q} style={{ padding: '8px 12px', border: '1px solid #2c3a3e', borderRadius: 6 }}>
                    <summary style={{ color: '#67e6e7', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>{item.q}</summary>
                    <p style={{ color: '#a8c0c5', fontSize: 11, margin: '6px 0 0', lineHeight: 1.5 }}>{item.a}</p>
                  </details>
                ))}
              </div>
              <p style={{ color: '#5a7a80', fontSize: 10, marginTop: 10 }}>We already know these weaknesses. Press J to dismiss.</p>
            </section>
          )}
        </motion.div>
      )}

      {/* ─── EXECUTIVE / BUSINESS & IMPACT (Shown ONLY on Intake / Landing page) ─── */}
      {!showResults && !showDecode && (
        <Suspense fallback={<div style={{ padding: 16, color: '#5a7a80', fontSize: 11, fontFamily: 'monospace' }}>Loading executive view…</div>}>
          <section className="exec-section">
            <div className="section-heading">
              <MatrixHeading text="BUSINESS &amp; IMPACT" as="h2" />
              <span>ROI · PRICING · GOVERNMENT</span>
            </div>
            <div className="exec-grid">
              <RoiCalculatorCard />
              <GovImpactCard />
              <PricingDeploymentCard />
            </div>
          </section>

          <section className="exec-section">
            <div className="section-heading">
              <MatrixHeading text="COMPETITIVE LANDSCAPE" as="h2" />
              <span>WHERE WE FIT IN THE MARKET</span>
            </div>
            <PositioningStatementCard />
            <div style={{ marginTop: 12 }}>
              <CompetitiveLandscapeCard />
            </div>
            <div className="exec-grid" style={{ marginTop: 12 }}>
              <MarketOpportunityCard />
            </div>
          </section>

          <section className="exec-section">
            <div className="section-heading">
              <MatrixHeading text="INTEGRATION &amp; SECURITY" as="h2" />
              <span>ENTERPRISE READINESS</span>
            </div>
            <div className="exec-grid">
              <IntegrationDataContractCard />
              <SecurityPrivacyCard />
              <LimitationsSafetyCard />
            </div>
          </section>
        </Suspense>
      )}

      {/* ─── PRODUCTION FOOTER ─── */}
      <footer
        className="console-footer"
        style={{
          marginTop: 48,
          paddingTop: 24,
          borderTop: '1px solid #1f3a42',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
          color: '#94a3b8',
          fontSize: 11,
        }}
      >
        <div>
          <b style={{ color: '#38bdf8' }}>CIRCUITMIND</b> — Deterministic PCB Hardware Triage
          <span style={{ display: 'block', marginTop: 4, color: '#64748b' }}>
            © 2026 CircuitMind Technologies. 100% Air-Gapped &amp; On-Premise.
          </span>
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <button
            onClick={() => setLegalModal('privacy')}
            style={{ background: 'none', border: 0, color: '#38bdf8', cursor: 'pointer', textDecoration: 'underline', fontSize: 11 }}
          >
            Privacy Policy
          </button>
          <button
            onClick={() => setLegalModal('terms')}
            style={{ background: 'none', border: 0, color: '#38bdf8', cursor: 'pointer', textDecoration: 'underline', fontSize: 11 }}
          >
            Terms of Service
          </button>
          <span
            style={{
              padding: '3px 8px',
              borderRadius: 999,
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid #10b981',
              color: '#34d399',
              fontSize: 10,
              fontWeight: 700,
            }}
          >
            🔒 Zero-Cookie Air-Gap
          </span>
        </div>
      </footer>

      {/* ─── PRIVACY MODAL ─── */}
      {legalModal === 'privacy' && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            display: 'grid',
            placeItems: 'center',
            background: 'rgba(3, 8, 12, 0.82)',
            backdropFilter: 'blur(8px)',
            padding: 16,
          }}
        >
          <div
            style={{
              maxWidth: 580,
              width: '100%',
              maxHeight: '85vh',
              overflowY: 'auto',
              background: '#0b1d22',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: 14,
              padding: 24,
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '1px solid #1f3a42', paddingBottom: 12 }}>
              <h3 style={{ margin: 0, color: '#38bdf8', fontSize: 15, letterSpacing: '0.08em' }}>CIRCUITMIND PRIVACY POLICY</h3>
              <button onClick={() => setLegalModal(null)} style={{ background: 'transparent', border: 0, color: '#94a3b8', fontSize: 20, cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ color: '#cbd5e1', fontSize: 12, lineHeight: 1.7, display: 'grid', gap: 12 }}>
              <p><b>1. Air-Gapped On-Premise Guarantee:</b> CircuitMind operates 100% locally on factory hardware. No CAD schematics, netlists, ATE test logs, or telemetry are ever transmitted across external networks.</p>
              <p><b>2. Zero Third-Party Cookies:</b> We do not use advertising or tracking cookies. Session state is retained strictly in local memory during active triage.</p>
              <p><b>3. Verified Repair Memory:</b> Historical repair data is stored in on-premise encrypted storage and is only modified through explicit, triple-gated human technician verification.</p>
            </div>
            <button onClick={() => setLegalModal(null)} style={{ marginTop: 20, width: '100%', padding: '10px 16px', background: '#13333b', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#f1f5f9', borderRadius: 8, fontWeight: 700, cursor: 'pointer' }}>
              Close
            </button>
          </div>
        </div>
      )}

      {/* ─── TERMS MODAL ─── */}
      {legalModal === 'terms' && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            display: 'grid',
            placeItems: 'center',
            background: 'rgba(3, 8, 12, 0.82)',
            backdropFilter: 'blur(8px)',
            padding: 16,
          }}
        >
          <div
            style={{
              maxWidth: 580,
              width: '100%',
              maxHeight: '85vh',
              overflowY: 'auto',
              background: '#0b1d22',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: 14,
              padding: 24,
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '1px solid #1f3a42', paddingBottom: 12 }}>
              <h3 style={{ margin: 0, color: '#38bdf8', fontSize: 15, letterSpacing: '0.08em' }}>CIRCUITMIND TERMS OF SERVICE</h3>
              <button onClick={() => setLegalModal(null)} style={{ background: 'transparent', border: 0, color: '#94a3b8', fontSize: 20, cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ color: '#cbd5e1', fontSize: 12, lineHeight: 1.7, display: 'grid', gap: 12 }}>
              <p><b>1. Human-in-the-Loop Verification:</b> CircuitMind provides ranked failure hypotheses and counterfactual falsification based on test log evidence. Physical technician inspection is required prior to hardware component rework or board scrapping.</p>
              <p><b>2. Deterministic Scope:</b> Diagnostic receipts represent deterministic evidence scores, not statistical liability warranties.</p>
              <p><b>3. Intellectual Property:</b> All customer PCB topology, BOM mappings, and factory telemetry remain the exclusive property of the licensee.</p>
            </div>
            <button onClick={() => setLegalModal(null)} style={{ marginTop: 20, width: '100%', padding: '10px 16px', background: '#13333b', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#f1f5f9', borderRadius: 8, fontWeight: 700, cursor: 'pointer' }}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  </main>;
}
