from datetime import datetime, timezone
import pandas as pd
from time import perf_counter
from typing import Dict, Any, List, Optional

from engine.signature_extractor import SignatureExtractor
from engine.topology_dag import TopologyDAG
from engine.semantic_memory import SemanticMemory
from engine.evidence_fusion import EvidenceFusion
from engine.narrative_generator import NarrativeGenerator
from engine import fault_modes, repair_memory, versions as engine_versions
from engine.data_quality import analyze_board_log
from engine.test_integrity import summarize_test_status
from engine.ood import detect_novelty
from engine.multi_fault_solver import solve_multi_fault

DOMAIN_CODES = {'POWER': 'P', 'DIGITAL': 'D', 'COMMS': 'C', 'ANALOG': 'A', 'OTHER': 'O'}


class CircuitMindOrchestrator:
    """
    Master pipeline controller.
    Executes the 5 engines in sequence.
    """
    def __init__(self, memory_history_path: str = None, memory_logs_path: str = None):
        # Initialize all 5 layers. The memory corpus defaults to the frozen
        # repair history, merged with any *verified* learned cases when they
        # exist (demo-scoped learning never touches the validated corpus).
        if memory_history_path is None:
            memory_history_path = repair_memory.combined_history_path() or str(repair_memory.FROZEN_HISTORY)
        self.extractor = SignatureExtractor()
        self.dag = TopologyDAG()
        self.memory = SemanticMemory(history_path=memory_history_path, logs_path=memory_logs_path)
        self.fusion = EvidenceFusion()
        self.narrator = NarrativeGenerator()
        self.fault_mode_library = fault_modes.load_fault_modes()
        
    def analyze(self, board_id: str, test_logs: pd.DataFrame, repair_notes: str = "") -> Dict[str, Any]:
        """
        Runs the full deterministic pipeline for a given board.
        Returns a complete forensic report dict.

        ``repair_notes`` is optional free text for the current session (for
        example "replaced R12" or "cold solder at U3"). When present it is
        folded into historical retrieval and evidence fusion; when empty the
        pipeline is byte-for-byte identical to the validated baseline.
        """
        board_logs = test_logs[test_logs['board_id'] == board_id]
        if board_logs.empty:
            raise ValueError(f"No test rows found for board '{board_id}'.")
        timeline: List[Dict[str, Any]] = []

        def run_stage(label: str, detail: str, operation):
            started = perf_counter()
            result = operation()
            timeline.append({
                'label': label,
                'detail': detail,
                'duration_ms': round((perf_counter() - started) * 1000, 2),
                'status': 'complete',
            })
            return result
        
        # Layer 1: Extract Signature
        sig = run_stage(
            'Failure signature extracted',
            'Measured deviations, severity, and domain profile computed from the uploaded test log.',
            lambda: self.extractor.extract(board_logs),
        )
        
        report = {
            'board_id': board_id,
            'status': 'PASS' if sig['severity_label'] == 'PASS' else 'FAIL',
            'signature': sig,
            'evidence_policy': self.fusion.get_policy(),
            'repair_notes': repair_notes.strip()[:2000],
        }
        
        if report['status'] == 'PASS':
            report['timeline'] = timeline
            report['diagnosis_state'] = 'PASS'
            report['evidence_ledger'] = []
            report['narrative'] = self.narrator.generate(report)
            return report
            
        # Layer 2: Causal Topology
        failed_nets = [t['net'] for t in sig['failed_tests'] if t['net'] != 'UNKNOWN']
        dag_res = run_stage(
            'Topology analyzed',
            'Primary nets, cascade paths, and component relationships were derived from the board dependency graph.',
            lambda: self.dag.analyze_cascades(failed_nets),
        )
        report['dag_analysis'] = dag_res
        
        # Layer 3: Semantic Memory
        mem_res = run_stage(
            'Historical precedents retrieved',
            'TF-IDF retrieval searched the local repair-history corpus.',
            lambda: self.memory.search(sig, extra_text=repair_notes),
        )
        report['semantic_memory'] = mem_res
        
        # Layer 4: Evidence Fusion
        suspects = run_stage(
            'Evidence fused',
            'Named history, net, topology, BOM, and category evidence streams were combined.',
            lambda: self.fusion.score_candidates(sig, dag_res, mem_res, notes=repair_notes),
        )
        report['suspects'] = suspects

        # Coverage: how many observed failures each candidate explains, used
        # by the Hypothesis Arena's counterfactual challenge and WHY NOT panel.
        self.fusion.compute_coverage(suspects, sig, self.dag)

        # Mechanism-aware fault modes + expected-vs-observed reasoning. Every
        # hypothesis becomes component + fault mode, and each candidate's
        # expected blast radius comes from its fault mechanism (functional
        # dependency), NOT from electrical reachability alone.
        passing_nets = {
            str(row['net']).strip()
            for _, row in board_logs.iterrows()
            if str(row.get('pass_fail', '')).upper() == 'PASS'
            and not pd.isna(row.get('net')) and str(row['net']).strip() != 'UNKNOWN'
        }
        self._assign_fault_modes(suspects, sig, passing_nets)

        # Failure Fingerprint — a compact, memorable identity for the board's
        # failure pattern (e.g. P94-D71-C24-A12 | 4F | 1R | 3C).
        report['fingerprint'] = self._compute_fingerprint(sig, dag_res)
        report['fingerprint_segments'] = self._fingerprint_segments(sig, dag_res)

        # Multi-fault detection: flag when evidence suggests independent faults.
        report['multi_fault'] = self._detect_multi_fault(suspects, sig, dag_res)

        # Multi-fault *explanation*: sparse set-cover solver with a parsimony
        # penalty (best single vs best two-fault hypothesis).
        report['multi_fault_analysis'] = solve_multi_fault(
            suspects,
            [t['test_step'] for t in sig.get('failed_tests', [])],
            self.fusion.knobs.get('multi_fault', {}),
        )

        # Test observability: which functions/components the failed tests observe.
        report['observability'] = self.dag.analyze_observability(sig.get('failed_tests', []))

        # Single computed citation object: the historical precedent that best
        # supports the leading suspect. The evidence card, narrative, evidence
        # ledger, and PDF report all read this one object, so every surface
        # cites the same case and the same similarity score.
        report['cited_precedent'] = self._resolve_cited_precedent(suspects, mem_res)
        self._normalize_leading_evidence(suspects, report['cited_precedent'])
        report['confidence_tier'] = self._confidence_tier(suspects)

        # OOD / novelty state: does this failure pattern have sufficient
        # historical + structural support? Independent axis from the ranking.
        report['ood_state'] = detect_novelty(
            sig, mem_res, suspects[0] if suspects else None,
            report['cited_precedent'],
            report['multi_fault']['multi_fault_likely'],
            self.fusion.knobs.get('ood', {}),
        )
        # Honest-uncertainty rule: a NOVEL pattern never receives a confident
        # tier. The ranking still stands, but the presentation must say the
        # evidence is insufficient for a strong claim. Benchmark boards are
        # KNOWN patterns, so the validated numbers are unaffected.
        if report['ood_state']['state'] == 'NOVEL' and report['confidence_tier'] == 'Strong Evidence':
            report['confidence_tier'] = 'Insufficient Evidence'

        # Data-quality gate for this board's log.
        report['data_quality'] = analyze_board_log(
            board_logs, self.extractor.test_map, sig
        )

        # Test integrity: ABORT/NOT_EXECUTED/SKIPPED/INVALID are never treated
        # as PASS or as PCB failures; sequence gaps and contradictions are
        # surfaced before diagnosis is trusted.
        report['test_integrity'] = summarize_test_status(board_logs)

        # Version identity for reproducibility.
        report['versions'] = dict(engine_versions.VERSIONS)
        
        # Determine Next Best Test
        nbt = run_stage(
            'Verification path selected',
            'The next physical test was chosen only when leading hypotheses remain close.',
            lambda: self.fusion.get_next_best_test(suspects, sig),
        )
        report['next_best_test'] = nbt
        report['timeline'] = timeline

        # Data-quality gating (Bug B): a RED input never yields a confident
        # diagnosis. State machine: ABSTAIN (RED) -> DEGRADED (AMBER) ->
        # VALID/INCONCLUSIVE (GREEN). The ranking is still computed for
        # candidate exploration, but an ABSTAIN report says so explicitly and
        # never claims a reliable diagnosis.
        dq_status = report.get('data_quality', {}).get('status', 'GREEN')
        if dq_status == 'RED':
            report['diagnosis_state'] = 'ABSTAIN'
            report['abstain_reason'] = (
                "Insufficient evidence for a reliable diagnosis: the log is missing "
                "critical attribution (see data quality issues). Candidates below are "
                "exploration only — resolve the evidence gaps first."
            )
            report['required_next_info'] = [
                issue['message'] for issue in report.get('data_quality', {}).get('issues', [])[:5]
            ] or ['Obtain a complete, attributed test log for this board.']
        elif dq_status == 'AMBER':
            report['diagnosis_state'] = 'DEGRADED'
        elif nbt.get('active'):
            report['diagnosis_state'] = 'INCONCLUSIVE'
        else:
            report['diagnosis_state'] = 'LEADING_HYPOTHESIS'
        # A NOVEL pattern is never presented as a confident leading hypothesis.
        if report.get('ood_state', {}).get('state') == 'NOVEL' and report['diagnosis_state'] == 'LEADING_HYPOTHESIS':
            report['diagnosis_state'] = 'INCONCLUSIVE'
        report['evidence_ledger'] = self._build_evidence_ledger(sig, dag_res, mem_res, suspects, report['cited_precedent'])

        # Case file number: an institutional identity for this investigation,
        # surfaced in the results header, PDF dossier, and CSV export.
        report['case_number'] = self._case_number(board_id, suspects)

        # Phase 18 — 'What would change my mind?'
        report['verdict_flip'] = self._verdict_flip(
            suspects, sig, report.get('next_best_test'), report.get('multi_fault_analysis')
        )

        # Known investigation gaps: specific, honest statements of what THIS
        # investigation could not know. Surfaced as the "confession panel" —
        # voluntary disclosure that signals confidence.
        report['investigation_gaps'] = self._investigation_gaps(sig, dag_res, mem_res, suspects, report)

        # Diagnostic Contract — single structured contract object
        report['diagnostic_contract'] = self._build_diagnostic_contract(
            board_id=board_id,
            case_number=report['case_number'],
            sig=sig,
            suspects=suspects,
            report=report,
            board_logs=board_logs,
        )

        # Layer 5: Narrative Generation
        report['narrative'] = self.narrator.generate(report)
        
        return report

    @staticmethod
    def _resolve_cited_precedent(suspects: List[Dict], memory: Dict) -> Optional[Dict]:
        """Return the single historical match that best supports the leading suspect."""
        if not suspects or not memory.get('matches'):
            return None
        top_refdes = suspects[0]['refdes']
        supporting = [
            match for match in memory['matches']
            if str(match.get('root_cause_component', '')) == top_refdes
        ]
        if not supporting:
            return None
        return max(supporting, key=lambda match: float(match.get('similarity', 0)))

    @staticmethod
    def _canonical_history_line(match: Dict) -> str:
        """One canonical phrasing for the cited precedent, used everywhere."""
        return (
            f"Historical case {match['repair_id']} identifies {match['root_cause_component']} "
            f"({float(match.get('similarity', 0)):.0f}% symptom match)."
        )

    @classmethod
    def _normalize_leading_evidence(cls, suspects: List[Dict], cited_precedent: Optional[Dict]) -> None:
        """Make the leading card's history line read from the cited precedent."""
        if not suspects:
            return
        top = suspects[0]
        top['positive_evidence'] = [
            line for line in top['positive_evidence']
            if not line.startswith('Historical case ')
        ]
        if cited_precedent:
            top['positive_evidence'].insert(0, cls._canonical_history_line(cited_precedent))

    def _assign_fault_modes(self, suspects: List[Dict], sig: Dict, passing_nets: set) -> None:
        """Enrich every candidate into a component + fault-mode hypothesis with
        mechanism-based expected-vs-observed coverage."""
        comps = self.fusion.df_comps
        for cand in suspects:
            refdes = cand['refdes']
            own_net = str(cand.get('net', '')).strip()
            downstream_comps = self.dag.get_functional_downstream_components(refdes)
            downstream_nets = set()
            for comp in downstream_comps:
                if comp in comps.index:
                    downstream_nets.add(str(comps.loc[comp, 'net']).strip())
            expected = fault_modes.expected_affected_nets(own_net, downstream_nets)
            relevant = [t for t in sig.get('failed_tests', []) if t.get('net', '') in expected]
            cand['fault_mode'] = fault_modes.assign_fault_mode(
                str(cand.get('cat', '')), relevant, self.fault_mode_library
            )
            cand['expected_nets'] = sorted(expected)
            cand['expected_vs_observed'] = fault_modes.expected_vs_observed(
                expected, sig.get('failed_tests', []), passing_nets
            )

    @staticmethod
    def _verdict_flip(suspects: List[Dict], sig: Dict, nbt: Dict, mfa: Dict) -> List[Dict]:
        """Phase 18 — 'What would change my mind?' Derived from real mechanism
        data, never invented:

        - failures OUTSIDE the leader's mechanism: if one of these proves
          healthy, the leader's coverage rises (it stops looking like a
          multi-fault board).
        - failures the runner-up explains but the leader does not: if one of
          these proves healthy, the runner-up loses its differentiator.
        - the active Next Best Test, when present, is literally the planned
          mind-changer.
        - the multi-fault solver's residual, when present, is the second
          fault's only leg to stand on.
        """
        flip: List[Dict] = []
        if not suspects:
            return flip
        leader = suspects[0]
        runner = suspects[1] if len(suspects) > 1 else None
        evo = leader.get('expected_vs_observed') or {}
        unexpected = evo.get('unexpected') or []
        if unexpected:
            flip.append({
                'observation': f"{'/'.join(unexpected[:3])} proves NOMINAL",
                'effect': (
                    f"That failure is outside {leader['refdes']}'s mechanism. If it is healthy, "
                    f"the leader's coverage rises and the multi-fault picture weakens."
                ),
            })
        if runner:
            runner_evo = runner.get('expected_vs_observed') or {}
            runner_only = [t for t in (runner_evo.get('explained') or []) if t not in (evo.get('explained') or [])]
            if runner_only:
                flip.append({
                    'observation': f"{'/'.join(runner_only[:3])} proves NOMINAL",
                    'effect': (
                        f"It is the only failure {runner['refdes']} explains that {leader['refdes']} does not — "
                        f"a healthy reading removes the runner-up's differentiator."
                    ),
                })
        if nbt and nbt.get('active'):
            flip.append({
                'observation': nbt['test'],
                'effect': nbt['reason'],
            })
        mfa = mfa or {}
        residual = mfa.get('unexplained_after_single') or []
        if residual:
            flip.append({
                'observation': f"{'/'.join(residual[:3])} confirms a second fault",
                'effect': "The two-fault hypothesis stands on exactly this residual — it is the evidence that justifies a second independent fault.",
            })
        return flip

    @staticmethod
    def _confidence_tier(suspects: List[Dict]) -> str:
        """Derive an honest confidence tier from the leading evidence score."""
        if not suspects:
            return 'PASS'
        score = float(suspects[0]['score'])
        if score >= 70.0:
            return 'Strong Evidence'
        if score >= 50.0:
            return 'Moderate Evidence'
        return 'Insufficient Evidence'

    @staticmethod
    def _case_number(board_id: str, suspects: List[Dict]) -> str:
        """Institutional case identity: CM-YYYY-MM-BOARD-SUSPECT."""
        from datetime import date
        clean = ''.join(ch for ch in str(board_id) if ch.isalnum())[:12] or 'BOARD'
        suspect = suspects[0]['refdes'] if suspects else 'PASS'
        today = date.today()
        return f'CM-{today.year}-{today.month:02d}-{clean}-{suspect}'

    @staticmethod
    def _investigation_gaps(sig: Dict, dag: Dict, memory: Dict, suspects: List[Dict], report: Dict) -> List[Dict]:
        """
        Known investigation gaps — specific, honest statements of what this
        investigation could not know. Pure template generation; no scoring.
        """
        gaps: List[Dict[str, str]] = []
        unmapped = [
            t['test_step'] for t in sig.get('failed_tests', [])
            if t.get('net') == 'UNKNOWN'
        ]
        if unmapped:
            extra = f" and {len(unmapped) - 1} more" if len(unmapped) > 1 else ""
            gaps.append({
                'label': 'Unmapped test steps',
                'detail': (
                    f"Test step {unmapped[0]}{extra} is not mapped to any net in the "
                    "current topology, so its evidence could not be fused into the "
                    "ranking. If that step is electrically relevant, coverage "
                    "estimates may be incomplete."
                ),
            })
        if not report.get('cited_precedent') and not memory.get('matches'):
            gaps.append({
                'label': 'No historical precedent',
                'detail': (
                    "No repair-history case matches this failure signature. The "
                    "retrieval stream contributed reduced evidence, so the ranking "
                    "rests on net and topological evidence alone. Adding a confirmed "
                    "repair case after resolution would strengthen future matches."
                ),
            })
        elif suspects and memory.get('matches'):
            # History points AWAY from the leader: a genuine known gap.
            closest = memory['matches'][0]
            leader = suspects[0]['refdes']
            if str(closest.get('root_cause_component', '')) != leader:
                cited = report.get('cited_precedent')
                if cited:
                    detail = (
                        f"The closest historical match ({closest['repair_id']}, "
                        f"{float(closest['similarity']):.1f}% similarity) was resolved "
                        f"by addressing {closest['root_cause_component']}, not {leader}. "
                        f"A supporting precedent for {leader} exists "
                        f"({cited['repair_id']}, {float(cited['similarity']):.1f}%) but "
                        f"ranks below it, so the retrieval stream leans against the "
                        "leader and net/topological evidence carries the ranking."
                    )
                else:
                    detail = (
                        f"The closest historical match ({closest['repair_id']}, "
                        f"{float(closest['similarity']):.1f}% similarity) was resolved "
                        f"by addressing {closest['root_cause_component']}, not {leader}. "
                        "The retrieval stream therefore weighs against the leading "
                        "hypothesis, and the ranking rests on net and topological "
                        "evidence instead. A confirmed repair case for this pattern "
                        "would resolve the conflict."
                    )
                gaps.append({'label': 'Contradictory historical precedent', 'detail': detail})
        if suspects:
            leader = suspects[0]
            coverage = float(leader.get('coverage', 1.0))
            if coverage < 1.0:
                unexplained = leader.get('unexplained_failures', [])
                gap_text = (
                    f"The leading hypothesis {leader['refdes']} explains "
                    f"{coverage * 100:.0f}% of observed failures; "
                )
                if unexplained:
                    gap_text += (
                        f"{' '.join(unexplained[:3])} remain unexplained by any single "
                        "fault and may indicate an independent second fault."
                    )
                else:
                    gap_text += "some failure evidence could not be attributed to it."
                gaps.append({'label': 'Incomplete failure coverage', 'detail': gap_text})
        mf = report.get('multi_fault') or {}
        if mf.get('multi_fault_likely'):
            gaps.append({
                'label': 'Possible independent faults',
                'detail': (
                    "The failure pattern spans multiple electrical domains with no "
                    "single component upstream of every failing net. A second "
                    "independent fault cannot be ruled out without further testing."
                ),
            })
        return gaps

    @staticmethod
    def _compute_fingerprint(sig: Dict, dag: Dict) -> str:
        """Failure Fingerprint string: compact domain-level identity."""
        active = [
            (DOMAIN_CODES.get(d, d[:1]), min(100, int(v * 33.3)))
            for d, v in sig['domain_severity'].items() if v > 0
        ]
        active.sort(key=lambda x: -x[1])
        domain_str = '-'.join(f'{c}{s}' for c, s in active) or 'PASS'
        nf = len(sig.get('failed_tests', []))
        nr = len(dag.get('primary_nets', []))
        nc = len(dag.get('cascade_nets', []))
        return f'{domain_str} | {nf}F | {nr}R | {nc}C'

    @staticmethod
    def _fingerprint_segments(sig: Dict, dag: Dict) -> List[Dict]:
        """Structured fingerprint parts (code, severity, label) for the UI."""
        segments = []
        for domain, value in sig['domain_severity'].items():
            if value <= 0:
                continue
            segments.append({
                'code': DOMAIN_CODES.get(domain, domain[:1]),
                'domain': domain,
                'score': min(100, int(value * 33.3)),
            })
        segments.sort(key=lambda x: -x['score'])
        return segments

    @staticmethod
    def _detect_multi_fault(suspects: List[Dict], sig: Dict, dag: Dict) -> Dict:
        """Detect indicators of multiple independent faults."""
        if not suspects:
            return {'multi_fault_likely': False, 'indicators': []}
        leader = suspects[0]
        indicators = []
        coverage = leader.get('coverage', 1.0)
        if coverage < 0.70:
            unexplained = leader.get('unexplained_failures', [])
            indicators.append(
                f"Leading hypothesis {leader['refdes']} explains only "
                f"{coverage * 100:.0f}% of observed failures: "
                f"{' '.join(unexplained[:3])} remain unexplained."
            )
        primary_nets = dag.get('primary_nets', [])
        if len(primary_nets) >= 2:
            indicators.append(
                f"{len(primary_nets)} independent primary failing nets detected: "
                f"{' '.join(primary_nets[:3])}."
            )
        failed_domains = {t.get('domain', '?') for t in sig.get('failed_tests', [])}
        if len(failed_domains) >= 3:
            indicators.append(
                f"Failures span {len(failed_domains)} electrical domains "
                f"({' '.join(sorted(failed_domains))})."
            )
        return {
            'multi_fault_likely': len(indicators) >= 2,
            'indicators': indicators,
        }

    @staticmethod
    def _build_evidence_ledger(signature: Dict, dag: Dict, memory: Dict, suspects: List[Dict], cited_precedent: Optional[Dict] = None) -> List[Dict]:
        """Build source-addressable evidence records for the UI and PDF report."""
        ledger: List[Dict] = []
        for index, test in enumerate(signature.get('failed_tests', []), start=1):
            ledger.append({
                'id': f'E{index:02d}',
                'source': 'Test log',
                'strength': signature.get('severity_label', 'MEDIUM'),
                'observation': f"{test['test_step']} failed on {test['net']} (deviation {test['deviation']:.2f}).",
            })
        offset = len(ledger)
        for index, path in enumerate(dag.get('causal_paths', [])[:4], start=1):
            ledger.append({
                'id': f'E{offset + index:02d}',
                'source': 'Dependency graph',
                'strength': 'HIGH',
                'observation': f"{path['source_net']} reaches {path['symptom_net']} through {' → '.join(path['path'])}.",
            })
        if cited_precedent:
            ledger.append({
                'id': f'E{len(ledger) + 1:02d}',
                'source': 'Repair history',
                'strength': 'MEDIUM',
                'observation': f"{cited_precedent['repair_id']} is a {float(cited_precedent['similarity']):.1f}% symptom match for {cited_precedent['root_cause_component']}.",
            })
        if suspects:
            top = suspects[0]
            ledger.append({
                'id': f'E{len(ledger) + 1:02d}',
                'source': 'Evidence fusion',
                'strength': 'HIGH',
                'observation': f"{top['refdes']} has the leading deterministic evidence score of {top['score']:.1f}/100.",
            })
        return ledger

    @classmethod
    def _extract_source_timestamp(
        cls,
        report: Dict[str, Any],
        sig: Dict[str, Any],
        board_logs: Optional[pd.DataFrame] = None,
    ) -> str:
        """Return the source test event timestamp if available; otherwise current UTC ISO time."""
        if report.get('timestamp'):
            return str(report['timestamp'])
        if sig.get('timestamp'):
            return str(sig['timestamp'])

        if board_logs is not None and isinstance(board_logs, pd.DataFrame) and not board_logs.empty:
            candidates = ('timestamp', 'test_timestamp', 'time', 'test_time', 'datetime', 'date', 'created_at', 'test_date')
            for col in candidates:
                if col in board_logs.columns:
                    series = board_logs[col].dropna().astype(str).str.strip()
                    series = series[series != '']
                    if not series.empty:
                        return str(series.iloc[0])

        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _build_diagnostic_contract(
        cls,
        board_id: str,
        case_number: str,
        sig: Dict[str, Any],
        suspects: List[Dict[str, Any]],
        report: Dict[str, Any],
        board_logs: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Assemble the single structured diagnostic contract object."""
        failed_tests = sig.get('failed_tests', [])
        deviations = [float(t.get('deviation', 0)) for t in failed_tests if t.get('deviation') is not None]
        dev_range = [round(min(deviations), 2), round(max(deviations), 2)] if deviations else [0.0, 0.0]

        top = suspects[0] if suspects else None
        top_evo = (top.get('expected_vs_observed') or {}) if top else {}
        top_fault_mode = (top.get('fault_mode') or {}) if top else {}

        # 1. OBSERVED
        observed = {
            'failed_test_count': len(failed_tests),
            'primary_domain': str(sig.get('primary_domain', 'UNKNOWN')),
            'severity': str(sig.get('severity_label', 'UNKNOWN')),
            'deviation_range': dev_range,
            'failed_tests': [str(t.get('test_step', '')) for t in failed_tests],
            'fingerprint': str(report.get('fingerprint', '')),
        }

        # 2. INFERRED
        inferred = {
            'leading_refdes': str(top['refdes']) if top else '',
            'leading_desc': str(top['desc']) if top else '',
            'evidence_score': float(top['score']) if top else 0.0,
            'fault_mode': str(top_fault_mode.get('label') or top_fault_mode.get('code')) if (top and top_fault_mode.get('label') or top_fault_mode.get('code')) else None,
            'mechanism_coverage_pct': int(top_evo.get('coverage_pct', top.get('coverage_pct', 0))) if top else 0,
            'mechanism_explained': [str(x) for x in top_evo.get('explained', top.get('explained_failures', []))] if top else [],
            'mechanism_unexplained': [str(x) for x in top_evo.get('unexpected', top.get('unexplained_failures', []))] if top else [],
            'confidence_tier': str(report.get('confidence_tier', 'Insufficient Evidence')),
            'diagnosis_state': str(report.get('diagnosis_state', 'INCONCLUSIVE')),
            'ood_state': str(report.get('ood_state', {}).get('state', 'UNKNOWN')),
        }

        # 3. REJECTED
        rejected = []
        if len(suspects) > 1:
            for alt in suspects[1:5]:
                alt_evo = alt.get('expected_vs_observed') or {}
                alt_cov = int(alt_evo.get('coverage_pct', alt.get('coverage_pct', 0)))
                alt_unexp = alt_evo.get('unexpected') or alt.get('unexplained_failures') or []
                
                if alt_cov >= 100:
                    reason = f"Covers failures electrically, but outweighed by leading evidence (score {alt['score']:.1f} vs {top['score']:.1f})."
                    gap = f"Score deficit of {top['score'] - alt['score']:.1f} pts; lower historical and topological alignment."
                else:
                    reason = f"Mechanism covers only {alt_cov}% of failures; {len(alt_unexp)} failure(s) fall outside its blast radius."
                    gap = f"Cannot explain {', '.join(alt_unexp[:3])} without assuming an independent second fault."

                rejected.append({
                    'refdes': str(alt['refdes']),
                    'desc': str(alt['desc']),
                    'score': float(alt['score']),
                    'mechanism_coverage_pct': alt_cov,
                    'rejection_reason': reason,
                    'evidence_gap': gap,
                })

        # 4. RECOMMENDED
        nbt = report.get('next_best_test') or {}
        dq_status = report.get('data_quality', {}).get('status', 'GREEN')
        conf_tier = report.get('confidence_tier', 'Moderate Evidence')

        if dq_status == 'RED' or report.get('diagnosis_state') == 'ABSTAIN':
            action = "ABSTAIN"
            target = "DATA_QUALITY"
            rationale = str(report.get('abstain_reason', "Insufficient evidence for reliable diagnosis."))
            nbt_payload = None
        elif nbt.get('active'):
            action = "VERIFY_FIRST"
            target = str(nbt.get('test', ''))
            rationale = str(nbt.get('reason', ''))
            nbt_payload = nbt
        elif conf_tier == 'Insufficient Evidence':
            action = "VERIFY_FIRST"
            target = str(top['refdes']) if top else "UNKNOWN"
            rationale = f"Verify {top['net']} impedance to ground before replacing {top['refdes']}." if top else "Insufficient evidence."
            nbt_payload = None
        else:
            action = "INSPECT"
            target = str(top['refdes']) if top else "UNKNOWN"
            rationale = f"Isolate and inspect {top['refdes']} ({top['desc']}). Verify {top['net']} impedance to ground before applying power." if top else "Inspect candidate."
            nbt_payload = None

        recommended = {
            'action': action,
            'target': target,
            'rationale': rationale,
            'next_best_test': nbt_payload,
        }

        # 5. VERIFICATION
        verification = {
            'state': 'PENDING_VERIFICATION',
            'technician_confirmed': False,
            'physical_repair_recorded': False,
            'retest_passed': False,
            'verified_repair': False,
            'repair_memory_admitted': False,
            'disclaimer': 'Physical verification still required.',
        }

        # Timestamp: use existing source/test timestamp if present, else UTC fallback
        timestamp = cls._extract_source_timestamp(report, sig, board_logs)

        return {
            'case_number': str(case_number),
            'board_id': str(board_id),
            'timestamp': timestamp,
            'observed': observed,
            'inferred': inferred,
            'rejected': rejected,
            'recommended': recommended,
            'verification': verification,
        }

    def simulate_repair(self, original_report: Dict, refdes_to_replace: str) -> Dict:
        """What-if simulator — mechanism-based residual simulation.

        If ``refdes_to_replace`` were repaired, which observed failures are
        expected to resolve? The answer comes from the candidate's fault mode:
        a fault in a component affects its own net plus the nets of its
        functional downstream dependents (its expected blast radius, computed
        in ``_assign_fault_modes``). Failures outside that radius would remain
        — evidence of an independent second fault, never a claim that the board
        is fixed.

        This replaces the previous graph-direction shortcut (electrical
        reachability on ``primary_nets``), which resolved nothing on power-path
        boards because the DAG edge orientation does not represent current flow
        through passive devices (PASSIVE pins get ``net -> ref`` edges).
        """
        sig = original_report.get('signature', {})
        failed_tests = sig.get('failed_tests', [])
        suspects = original_report.get('suspects', [])
        cand = next((c for c in suspects if c.get('refdes') == refdes_to_replace), None)

        if cand is None:
            # Unknown component — nothing to simulate.
            return {
                'replaced': refdes_to_replace,
                'resolved_nets': [],
                'remaining_nets': sorted({
                    t.get('net', '') for t in failed_tests
                    if t.get('net') and t['net'] != 'UNKNOWN'
                }),
                'resolved_tests': [],
                'remaining_tests': [t['test_step'] for t in failed_tests],
                'success': False,
                'mechanism': 'Component is not in the board candidate universe — no simulation possible.',
            }

        expected_nets = set(cand.get('expected_nets') or [])
        resolved_tests = [t for t in failed_tests if t.get('net') in expected_nets]
        remaining_tests = [t for t in failed_tests if t.get('net') not in expected_nets]
        fm = cand.get('fault_mode') or {}
        fm_label = fm.get('label') or fm.get('code') or 'fault'

        return {
            'replaced': refdes_to_replace,
            'resolved_nets': sorted({t['net'] for t in resolved_tests if t.get('net')}),
            'remaining_nets': sorted({t.get('net', '') for t in remaining_tests if t.get('net')}),
            'resolved_tests': [t['test_step'] for t in resolved_tests],
            'remaining_tests': [t['test_step'] for t in remaining_tests],
            'success': len(remaining_tests) == 0,
            'mechanism': (
                f"Assuming {refdes_to_replace} / {fm_label}: a fault here is expected to "
                f"affect {', '.join(sorted(expected_nets)) or 'its own net only'}. Failures on "
                "those nets are predicted to resolve; anything left is outside this "
                "mechanism's blast radius and would point to an independent fault."
            ),
        }
