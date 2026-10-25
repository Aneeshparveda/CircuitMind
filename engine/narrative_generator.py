from typing import Dict, Any

class NarrativeGenerator:
    """
    Generates a multi-sentence forensic investigation summary from the report data.
    Pure template + data approach — zero LLM dependency.
    """
    def generate(self, report: Dict[str, Any]) -> str:
        board_id = report.get('board_id', 'UNKNOWN_BOARD')
        sig = report.get('signature', {})
        dag = report.get('dag_analysis', {})
        candidates = report.get('suspects', [])
        memory = report.get('semantic_memory', {})
        
        if not candidates:
            return f"Investigation complete for {board_id}. All tests passed. No faults detected."
            
        fail_count = len(sig.get('failed_tests', []))
        domain = sig.get('primary_domain', 'UNKNOWN')
        top = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else None
        
        primary_nets = len(dag.get('primary_nets', []))
        cascade_nets = len(dag.get('cascade_nets', []))
        
        # 1. Opening — hand-written branches by failure count so the summary
        #    reads like an investigator's notes, not a template fill-in.
        narrative = f"**FORENSIC SUMMARY FOR {board_id}**\n\n"
        if fail_count == 1:
            narrative += f"A single {domain} test failed. "
        elif fail_count <= 3:
            narrative += f"{fail_count} {domain} tests failed in quick succession. "
        else:
            narrative += (
                f"Widespread failure: {fail_count} tests across the {domain} domain fell out of specification. "
                f"Patterns like this usually trace to one upstream fault rather than {fail_count} independent problems. "
            )

        # 2. Causal
        if cascade_nets > 0:
            chain_lang = (
                f"The dependency graph groups them under {primary_nets} primary root net(s), "
                f"with {cascade_nets} downstream symptom net(s) riding the same causal chain."
            )
            narrative += f"{chain_lang} "
        else:
            narrative += "The dependency graph isolates the fault to a single primary net with no downstream cascades. "
            
        # 3. Evidence
        contract = report.get('diagnostic_contract')
        if contract:
            inf = contract.get('inferred', {})
            top_refdes = inf.get('leading_refdes', top['refdes'])
            top_desc = inf.get('leading_desc', top['desc'])
            top_score = float(inf.get('evidence_score', top['score']))
            tier = inf.get('confidence_tier') or report.get('confidence_tier') or 'Moderate Evidence'
            fault_mode = inf.get('fault_mode')
        else:
            top_refdes = top['refdes']
            top_desc = top['desc']
            top_score = float(top['score'])
            tier = report.get('confidence_tier') or 'Moderate Evidence'
            fault_mode = (top.get('fault_mode') or {}).get('label')

        article = 'an' if tier[:1].lower() in 'aeiou' else 'a'
        fault_clause = f" (hypothesized mechanism: {fault_mode})" if fault_mode else ""
        narrative += f"\n\nStructured evidence reasoning ranks **{top_refdes} ({top_desc})** first with a deterministic evidence score of {top_score:.1f}/100 — {article} **{tier}** classification{fault_clause}. "
        if runner_up:
            gap = top['score'] - runner_up['score']
            if gap >= 15:
                narrative += f"The runner-up, {runner_up['refdes']}, trails by {gap:.1f} points and is outweighed on net and topological evidence. "
            elif gap >= 5:
                narrative += f"The runner-up, {runner_up['refdes']}, is close ({gap:.1f} points) — a verification test is warranted before replacing parts. "
            else:
                narrative += f"The runner-up, {runner_up['refdes']}, is within {gap:.1f} points; the ranking is sensitive and should be treated as provisional. "

        # 3b. Inconclusive — say WHY confidence is low and what would resolve it.
        #     Not a restatement of uncertainty: a structural explanation.
        if tier == 'Insufficient Evidence':
            reasons = []
            mf = report.get('multi_fault') or {}
            if mf.get('multi_fault_likely'):
                reasons.append(
                    "the failure pattern spans multiple electrical domains with no single component "
                    "upstream of every failing net — consistent with either multiple independent faults "
                    "or a shared infrastructure failure not covered by the test plan"
                )
            if not report.get('cited_precedent') and not memory.get('matches'):
                reasons.append(
                    "no historical case matches this signature, so the ranking rests on net and "
                    "topological evidence alone"
                )
            if fail_count >= 3 and not mf.get('multi_fault_likely'):
                reasons.append(
                    f"{fail_count} failing tests sit at the boundary between one upstream fault "
                    f"and several coincident ones"
                )
            if reasons:
                narrative += (
                    "\n\nConfidence is below the decision threshold because "
                    + "; and ".join(reasons)
                    + ". "
                )
            narrative += (
                "This is an honest uncertainty signal, not a pipeline failure — the correct "
                "engineering response is a targeted verification measurement, not a parts swap. "
            )

        # 4. Historical — always the single cited precedent computed by the orchestrator
        precedent = report.get('cited_precedent')
        if precedent:
            narrative += f"\n\nThis failure pattern exhibits a {float(precedent['similarity']):.1f}% semantic similarity to historical case {precedent['repair_id']}, which was successfully resolved by addressing {precedent['root_cause_component']}. "
        elif memory.get('matches'):
            # History points elsewhere: say so explicitly instead of hiding it.
            closest = memory['matches'][0]
            narrative += (
                f"\n\nThe closest historical precedent ({closest['repair_id']}, "
                f"{float(closest['similarity']):.1f}% similarity) points to "
                f"{closest['root_cause_component']}, which does not match the leading hypothesis. "
                f"History is therefore weighted against {top['refdes']} in the fusion below; "
                f"the ranking rests on net and topological evidence instead. "
            )
            
        # 5. Recommendation
        nbt = report.get('next_best_test') or {}
        if nbt.get('active'):
            narrative += (
                f"\n\n**RECOMMENDATION:** Do not replace parts yet. Run {nbt['test']} "
                f"on {nbt['net']} first — it separates {top['refdes']} from {runner_up['refdes'] if runner_up else 'the runner-up'} "
                f"before any rework. If that measurement stays abnormal, inspect {top['refdes']} and verify {top['net']} impedance to ground."
            )
        elif tier == 'Insufficient Evidence':
            narrative += (
                f"\n\n**RECOMMENDATION:** Do not replace parts on this evidence alone. "
                f"Verify {top['net']} impedance to ground and re-measure the {domain} rail; "
                f"if the pattern persists, isolate {top['refdes']} from the net before condemning it."
            )
        else:
            narrative += f"\n\n**RECOMMENDATION:** Isolate and inspect {top['refdes']}. If replacing, verify {top['net']} impedance to ground before applying power."

        # 6. Diagnostic Contract — auditable decision trail
        if contract:
            obs = contract.get('observed', {})
            inf = contract.get('inferred', {})
            rej = contract.get('rejected', [])
            rec = contract.get('recommended', {})

            obs_cnt = obs.get('failed_test_count', fail_count)
            obs_dom = obs.get('primary_domain', domain)
            obs_sev = obs.get('severity', sig.get('severity_label', 'UNKNOWN'))
            dev_r = obs.get('deviation_range', [0.0, 0.0])

            inf_refdes = inf.get('leading_refdes', top_refdes)
            inf_desc = inf.get('leading_desc', top_desc)
            inf_score = float(inf.get('evidence_score', top_score))
            inf_mode = inf.get('fault_mode')
            mode_clause = f" Fault mode: {inf_mode}." if inf_mode else ""

            exp_cnt = len(inf.get('mechanism_explained', []))
            unexp_cnt = len(inf.get('mechanism_unexplained', []))
            tot_cnt = exp_cnt + unexp_cnt
            if tot_cnt > 0:
                cov_phrase = f"Mechanism covers {exp_cnt}/{tot_cnt} observed failures."
            else:
                cov_phrase = f"Mechanism covers {inf.get('mechanism_coverage_pct', 0)}% of observed failures."

            if rej:
                rej_phrase = "; ".join(f"{c['refdes']} (explains only {c.get('mechanism_coverage_pct', 0)}% by mechanism)" for c in rej[:2])
            else:
                rej_phrase = "No alternatives evaluated."

            nbt_active = bool(nbt.get('active', False))
            if nbt_active:
                rec_phrase = f"Run {nbt['test']} on {nbt['net']} — this separates {top_refdes} from the runner-up before any rework."
            else:
                rec_phrase = rec.get('rationale') or f"Isolate and inspect {top_refdes}. Verify {top.get('net', '')} impedance to ground before applying power."

            narrative += (
                f"\n\n---\n\n"
                f"**DIAGNOSTIC CONTRACT**\n\n"
                f"**OBSERVED:** {obs_cnt} test(s) failed across {obs_dom} domain. "
                f"Severity: {obs_sev}. "
                f"Deviations range from {dev_r[0]:.1f}x to {dev_r[1]:.1f}x.\n\n"
                f"**INFERRED:** {inf_refdes} ({inf_desc}) is the leading hypothesis with evidence score {inf_score:.1f}/100. "
                f"{cov_phrase}{mode_clause}\n\n"
                f"**REJECTED:** {rej_phrase}\n\n"
                f"**RECOMMEND:** {rec_phrase}\n\n"
                f"**WILL LEARN:** Only if a human verifies the repair, retests PASS, and confirms the diagnosis. CircuitMind does not learn from unverified predictions."
            )
        else:
            evo = top.get('expected_vs_observed') or {}
            explained = evo.get('explained') or []
            unexpected = evo.get('unexpected') or []
            nbt_active = nbt.get('active', False) if nbt else False
            narrative += (
                f"\n\n---\n\n"
                f"**DIAGNOSTIC CONTRACT**\n\n"
                f"**OBSERVED:** {fail_count} test(s) failed across {domain} domain. "
                f"Severity: {sig.get('severity_label', 'UNKNOWN')}. "
                f"Deviations range from {min((t.get('deviation', 0) for t in sig.get('failed_tests', [])), default=0):.1f}x to {max((t.get('deviation', 0) for t in sig.get('failed_tests', [])), default=0):.1f}x.\n\n"
                f"**INFERRED:** {top['refdes']} ({top['desc']}) is the leading hypothesis with evidence score {top['score']:.1f}/100. "
                f"Mechanism covers {len(explained)}/{len(explained) + len(unexpected)} observed failures." + (f" Fault mode: {top.get('fault_mode', {}).get('label', 'N/A')}." if top.get('fault_mode') else "") + "\n\n"
                f"**REJECTED:** " + ("; ".join(f"{c['refdes']} (explains only {c.get('coverage_pct', 0)}% by mechanism)" for c in candidates[1:3]) if len(candidates) > 1 else "No alternatives evaluated.") + "\n\n"
                f"**RECOMMEND:** " + (f"Run {nbt['test']} on {nbt['net']} — this separates {top['refdes']} from the runner-up before any rework." if nbt_active else f"Isolate and inspect {top['refdes']}. Verify {top['net']} impedance to ground before applying power.") + "\n\n"
                f"**WILL LEARN:** Only if a human verifies the repair, retests PASS, and confirms the diagnosis. CircuitMind does not learn from unverified predictions."
            )

        return narrative
