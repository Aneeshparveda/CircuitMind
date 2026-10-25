import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

class SignatureExtractor:
    """
    Layer 1: Extracts the Failure DNA signature from test logs.
    Computes statistical deviations for every failed test.
    """
    
    def __init__(self, test_net_map_path: str = None):
        test_net_map_path = test_net_map_path or str(DATA_DIR / 'test_net_map.csv')
        self.test_map = pd.read_csv(test_net_map_path).set_index('test_step').to_dict('index')
        
    def extract(self, test_logs: pd.DataFrame) -> Dict[str, Any]:
        """
        Takes standardized test logs for a SINGLE board.
        Returns the Failure DNA.
        """
        signature = {
            'failed_tests': [],
            'domain_severity': {'POWER': 0.0, 'DIGITAL': 0.0, 'COMMS': 0.0, 'ANALOG': 0.0, 'OTHER': 0.0},
            'max_deviation': 0.0,
            'primary_domain': 'UNKNOWN',
            'severity_label': 'UNKNOWN'
        }
        
        failures = test_logs[test_logs['pass_fail'] == 'FAIL']
        
        if failures.empty:
            signature['severity_label'] = 'PASS'
            return signature
            
        for _, row in failures.iterrows():
            step = row['test_step']
            meas = row['measured_value']
            emin = row['expected_min']
            emax = row['expected_max']
            err  = row['error_code']
            # A missing/empty/NaN error code is 'no error code' — never the
            # literal string 'NAN' (NaN floats are truthy, so `or ''` is NOT
            # enough). Keeps fingerprints, ledgers, and exports clean.
            if err is None or (isinstance(err, float) and err != err):
                err = ''
            else:
                err = str(err).strip().upper()
                if err in {'NAN', 'NONE', 'NULL', 'NA'}:
                    err = ''
            
            # Calculate Deviation Score
            if pd.isna(emin) or pd.isna(emax) or emin == emax:
                # Boolean/Functional test failure
                deviation = 3.0 # Default high severity for functional fail
            else:
                midpoint = (emax + emin) / 2.0
                half_range = (emax - emin) / 2.0
                if half_range == 0 or pd.isna(meas):
                    deviation = 3.0
                else:
                    deviation = float(abs(meas - midpoint) / half_range)
                    
            # Map to net and domain
            domain = 'OTHER'
            net = 'UNKNOWN'
            level = 99
            
            if step in self.test_map:
                domain = self.test_map[step]['domain']
                net = self.test_map[step]['net_name']
                level = self.test_map[step]['level']
                
            signature['domain_severity'][domain] += deviation
            
            signature['failed_tests'].append({
                'test_step': step,
                'net': net,
                'domain': domain,
                'level': level,
                'deviation': deviation,
                'error_code': err,
                'measured': None if pd.isna(meas) else float(meas),
                'expected_min': None if pd.isna(emin) else float(emin),
                'expected_max': None if pd.isna(emax) else float(emax),
                'unit': row.get('unit', '')
            })
            
            if deviation > signature['max_deviation']:
                signature['max_deviation'] = deviation
                
        # Determine overall severity
        max_dev = signature['max_deviation']
        if max_dev >= 3.0: signature['severity_label'] = 'CRITICAL'
        elif max_dev >= 2.0: signature['severity_label'] = 'HIGH'
        elif max_dev >= 1.0: signature['severity_label'] = 'MEDIUM'
        else: signature['severity_label'] = 'LOW'
        
        # Determine primary domain
        if sum(signature['domain_severity'].values()) > 0:
            signature['primary_domain'] = max(signature['domain_severity'].items(), key=lambda x: x[1])[0]
            
        return signature
