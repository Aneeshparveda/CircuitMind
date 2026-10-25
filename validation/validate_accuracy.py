import math
import pandas as pd
import time
import os
import sys
import json

# Add project root to path so we can import engine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.orchestrator import CircuitMindOrchestrator
from data.schema_adapter import standardize_dataframe

DOMAIN_BY_ROOT = {
    'J1': 'POWER', 'F1': 'POWER', 'U3': 'POWER', 'L1': 'POWER', 'C1': 'POWER', 'U2': 'POWER', 'C2': 'POWER',
    'U1': 'DIGITAL', 'U5': 'DIGITAL', 'U6': 'DIGITAL', 'R1': 'DIGITAL',
    'U4': 'COMMS', 'A1': 'COMMS',
    'R12': 'ANALOG', 'Q1': 'ANALOG',
}

def run_validation():
    print("CircuitMind — Forensic Diagnostic Engine Validation")
    print("===================================================\n")
    
    try:
        df_blind = pd.read_csv('validation/ground_truth_blind.csv')
        df_logs = pd.read_csv('data/test_logs.csv')
    except FileNotFoundError:
        print("Error: Datasets not found. Run 'python data/generate_synthetic.py' first.")
        return
        
    df_logs = standardize_dataframe(df_logs)
    
    orchestrator = CircuitMindOrchestrator()
    
    results = {
        'total': len(df_blind),
        'top1_correct': 0,
        'top3_correct': 0,
        'top5_correct': 0,
        'domain_correct': 0,
        'mrr_sum': 0.0,
        'ndcg3_sum': 0.0,
        'inference_times': []
    }
    # Per-miss bookkeeping for the error breakdown. A miss is any failing
    # board where the true root cause is not the top-1 suspect. Every miss is
    # classified by:
    #   in_top3          -> the truth was still surfaced in the arena (rank 2 or 3)
    #   low_confidence   -> the report's confidence tier was 'Insufficient Evidence'
    #   multi_fault      -> the multi-fault detector fired (independent faults)
    #   silent           -> truth OUTSIDE top-3 AND no multi-fault warning:
    #                       a wrong answer the system neither surfaced nor warned about
    misses = {'in_top3_but_ranked_second': 0, 'not_in_top3': 0,
              'low_confidence': 0, 'multi_fault_flagged': 0, 'silent_misses': 0}
    
    print(f"Running validation on blind set ({results['total']} boards)...\n")
    
    for _, row in df_blind.iterrows():
        board_id = row['board_id']
        true_root = row['root_cause']
        
        start_time = time.perf_counter()
        
        # Execute Engine
        report = orchestrator.analyze(board_id, df_logs)
        
        end_time = time.perf_counter()
        results['inference_times'].append(end_time - start_time)
        
        if report['status'] == 'PASS':
            continue
            
        suspects = report.get('suspects', [])
        suspect_refs = [s['refdes'] for s in suspects]
        
        # Metrics
        if suspect_refs and suspect_refs[0] == true_root:
            results['top1_correct'] += 1
            results['top3_correct'] += 1
        elif true_root in suspect_refs[:3]:
            results['top3_correct'] += 1
        if true_root in suspect_refs[:5]:
            results['top5_correct'] += 1
        if true_root in suspect_refs:
            rank = suspect_refs.index(true_root) + 1
            results['mrr_sum'] += 1.0 / rank
            if rank <= 3:
                results['ndcg3_sum'] += 1.0 / math.log2(rank + 1)
            
        true_domain = DOMAIN_BY_ROOT.get(true_root)
        if true_domain and report['signature']['primary_domain'] == true_domain:
            results['domain_correct'] += 1

        # Error breakdown — only for misses
        if not suspect_refs or suspect_refs[0] != true_root:
            in_top3 = true_root in suspect_refs[:3]
            tier = report.get('confidence_tier')
            mf = bool(report.get('multi_fault', {}).get('multi_fault_likely', False))
            if in_top3:
                misses['in_top3_but_ranked_second'] += 1
            else:
                misses['not_in_top3'] += 1
            if tier == 'Insufficient Evidence':
                misses['low_confidence'] += 1
            if mf:
                misses['multi_fault_flagged'] += 1
            if not in_top3 and not mf:
                misses['silent_misses'] += 1

    # Calculate final metrics
    top1_acc = (results['top1_correct'] / results['total']) * 100
    top3_acc = (results['top3_correct'] / results['total']) * 100
    top5_acc = (results['top5_correct'] / results['total']) * 100
    mrr = results['mrr_sum'] / results['total']
    ndcg3 = results['ndcg3_sum'] / results['total']
    dom_acc = (results['domain_correct'] / results['total']) * 100
    times = sorted(results['inference_times'])
    avg_time = sum(times) / len(times)
    median_time = times[len(times) // 2]
    p95_time = times[int(len(times) * 0.95) - 1]
    
    summary = {
        'dataset': 'Held-Out Instance Test — Known Fault Families',
        'instances': results['total'],
        'top1_accuracy': round(top1_acc, 1),
        'top3_accuracy': round(top3_acc, 1),
        'top5_accuracy': round(top5_acc, 1),
        'mrr': round(mrr, 4),
        'ndcg_at_3': round(ndcg3, 4),
        'domain_accuracy': round(dom_acc, 1),
        'average_inference_seconds': round(avg_time, 6),
        'median_inference_seconds': round(median_time, 6),
        'p95_inference_seconds': round(p95_time, 6),
        'worst_inference_seconds': round(max(times), 6),
        'error_breakdown': misses,
    }
    with open('validation/metrics.json', 'w', encoding='utf-8') as metrics_file:
        json.dump(summary, metrics_file, indent=2)

    print("VALIDATION RESULTS")
    print("------------------")
    print(f"Dataset:       Held-Out Instance Test — Known Fault Families")
    print(f"Instances:     {results['total']} fault instances")
    print(f"Top-1 Acc:     {summary['top1_accuracy']:.1f}%")
    print(f"Top-3 Acc:     {summary['top3_accuracy']:.1f}%")
    print(f"Top-5 Acc:     {summary['top5_accuracy']:.1f}%")
    print(f"MRR:           {summary['mrr']:.4f}")
    print(f"NDCG@3:        {summary['ndcg_at_3']:.4f}")
    print(f"Domain Acc:    {summary['domain_accuracy']:.1f}%")
    print(f"Avg Time:      {summary['average_inference_seconds']:.3f}s / board  (median {summary['median_inference_seconds']:.3f}s, p95 {summary['p95_inference_seconds']:.3f}s)")
    total_misses = misses['in_top3_but_ranked_second'] + misses['not_in_top3']
    print(f"\nERROR BREAKDOWN ({total_misses} top-1 misses — computed, not hardcoded)")
    print("---------------------------------")
    for key, value in misses.items():
        print(f"  {key}: {value}")
    print("\n✅ Validation complete. Measured metrics saved to validation/metrics.json.")
    return summary

if __name__ == "__main__":
    run_validation()
