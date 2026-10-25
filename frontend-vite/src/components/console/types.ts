export type EvidenceContribution = Record<string, number>;

export interface FailedTest {
  test_step: string;
  net: string;
  domain: string;
  deviation: number;
  measured: number | null;
  expected_min: number | null;
  expected_max: number | null;
  unit: string;
  error_code: string;
}

export interface FaultMode {
  code: string;
  label: string;
  verification?: string;
  mechanism?: string;
}

export interface ExpectedVsObserved {
  explained: string[];
  unexpected: string[];
  expected_but_passed: string[];
  coverage_pct: number;
}

export interface Candidate {
  refdes: string;
  desc: string;
  cat?: string;
  net: string;
  score: number;
  evidence_contributions: EvidenceContribution;
  positive_evidence: string[];
  negative_evidence: string[];
  coverage_pct?: number;
  coverage?: number;
  explained_failures?: string[];
  unexplained_failures?: string[];
  fault_mode?: FaultMode;
  expected_nets?: string[];
  expected_vs_observed?: ExpectedVsObserved;
}

export interface ComponentOption {
  refdes: string;
  desc: string;
  net: string;
}

export interface DiagnosisReport {
  board_id: string;
  status: 'PASS' | 'FAIL';
  diagnosis_state?: 'PASS' | 'INCONCLUSIVE' | 'LEADING_HYPOTHESIS' | 'DEGRADED' | 'ABSTAIN';
  abstain_reason?: string;
  required_next_info?: string[];
  signature: {
    severity_label: string;
    primary_domain: string;
    max_deviation: number;
    domain_severity: Record<string, number>;
    failed_tests: FailedTest[];
  };
  dag_analysis?: {
    primary_nets: string[];
    cascade_nets: string[];
    primary_suspects: string[];
    causal_paths: Array<{ source_net: string; symptom_net: string; path: string[] }>;
    dependency_graph_is_dag: boolean;
  };
  semantic_memory?: {
    matches: Array<{ repair_id: string; similarity: number; symptom_text: string; root_cause_component: string; fix_action: string }>;
    cases?: Array<{ repair_id: string; root_cause_component: string; x: number; y: number }>;
    pca_point?: [number, number];
  };
  suspects?: Candidate[];
  next_best_test?: {
    active: boolean;
    gap?: number;
    test?: string;
    net?: string;
    purpose?: string;
    reason?: string;
    why_this_test?: string;
    info_gain?: string;
    separation?: number;
    risk?: string;
    effort?: string;
    utility?: number;
    candidates_distinguished?: string[];
    expected_outcomes?: Record<string, string>;
  };
  timeline?: Array<{ label: string; detail: string; duration_ms: number; status: string }>;
  evidence_ledger?: Array<{ id: string; source: string; strength: string; observation: string }>;
  narrative?: string;
  confidence_tier?: string;
  repair_notes?: string;
  ground_truth?: string | null;
  evidence_policy?: { weights?: Record<string, number>; uncertainty_gap?: number; notes_bonus?: number };
  cited_precedent?: { repair_id: string; similarity: number; root_cause_component: string; symptom_text: string; fix_action: string } | null;
  fingerprint?: string;
  fingerprint_segments?: Array<{ code: string; domain: string; score: number }>;
  case_number?: string;
  investigation_gaps?: Array<{ label: string; detail: string }>;
  verdict_flip?: Array<{ observation: string; effect: string }>;
  multi_fault?: {
    multi_fault_likely: boolean;
    indicators: string[];
  };
  multi_fault_analysis?: {
    analyzable?: boolean;
    best_single?: { components: string[]; coverage_pct: number; explained_count: number; total: number };
    best_pair?: { components: string[]; coverage_pct: number; explained_count: number; total: number; residual_covered?: number; residual_total?: number } | null;
    improvement_pct?: number;
    verdict?: string;
    verdict_text?: string;
    unexplained_after_single?: string[];
  };
  ood_state?: {
    state: string;
    max_similarity: number;
    n_matches: number;
    indicators: Array<{ label: string; detail: string }>;
    is_novel: boolean;
  };
  data_quality?: {
    status: string;
    label: string;
    issues: Array<{ level: string; message: string }>;
    summary: { total_tests: number; failed_tests: number; unmapped_failed_tests: number; unknown_failed_steps: number };
  };
  observability?: {
    failed_functions: string[];
    observed_components: string[];
    unmapped_tests: string[];
  };
  diagnostic_contract?: DiagnosticContract;
  versions?: Record<string, string>;
}

export interface RejectedCandidateContract {
  refdes: string;
  desc: string;
  score: number;
  mechanism_coverage_pct: number;
  rejection_reason: string;
  evidence_gap: string;
}

export interface VerificationLifecycle {
  state: string;
  technician_confirmed: boolean;
  physical_repair_recorded: boolean;
  retest_passed: boolean;
  verified_repair: boolean;
  repair_memory_admitted: boolean;
  disclaimer: string;
}

export interface DiagnosticContract {
  case_number: string;
  board_id: string;
  timestamp: string;
  observed: {
    failed_test_count: number;
    primary_domain: string;
    severity: string;
    deviation_range: [number, number];
    failed_tests: string[];
    fingerprint: string;
  };
  inferred: {
    leading_refdes: string;
    leading_desc: string;
    evidence_score: number;
    fault_mode: string | null;
    mechanism_coverage_pct: number;
    mechanism_explained: string[];
    mechanism_unexplained: string[];
    confidence_tier: string;
    diagnosis_state: string;
    ood_state: string;
  };
  rejected: RejectedCandidateContract[];
  recommended: {
    action: string;
    target: string;
    rationale: string;
    next_best_test?: any;
  };
  verification: VerificationLifecycle;
}

export interface FleetRow {
  board_id: string;
  status: 'PASS' | 'FAIL' | 'ERROR';
  confidence_tier: string;
  top_refdes: string;
  top_score: number | null;
  failed_tests: number;
  fingerprint?: string;
  ground_truth?: string | null;
}

export interface ConsoleArgs {
  ui_state?: string;
  demo_cases?: Array<{ id: string; board_id: string; label: string; subtitle: string }>;
  selected_board?: string;
  selected_component?: string;
  board_ids?: string[];
  component_options?: ComponentOption[];
  uploaded_file?: { name: string; size?: number; demo: boolean } | null;
  report?: DiagnosisReport | null;
  simulation?: { replaced: string; resolved_nets: string[]; remaining_nets: string[]; success: boolean } | null;
  challenge_open?: boolean;
  error_message?: string;
  pdf_base64?: string;
  csv_base64?: string;
  fleet?: FleetRow[] | null;
  fleet_scan_ms?: number;
  verified_confirmation?: { added?: boolean; reason?: string; repair_id?: string; count?: number } | null;
  revealed_truth?: string | null;
  fleet_tester?: { state?: string; suspected_tests?: { test_step: string; boards_failed: number; boards_ran: number; failure_rate: number; attribution?: string; fixture_id?: string; fixture_fail_rate?: number; peer_fixture_fail_rate?: number }[]; note?: string } | null;
  max_upload_bytes?: number;
  validation_metrics?: {
    dataset?: string;
    instances?: number;
    top1_accuracy?: number;
    top3_accuracy?: number;
    domain_accuracy?: number;
    average_inference_seconds?: number;
    median_inference_seconds?: number;
    p95_inference_seconds?: number;
    inference_ms?: number;
    error_breakdown?: Record<string, number>;
    weights_note?: string;
    learned_weights?: Record<string, number>;
  };
}
