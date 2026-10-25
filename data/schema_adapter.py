import pandas as pd
from typing import Dict, List, Any


def validate_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate a raw DataFrame before standardization.

    Returns {valid: bool, errors: list, warnings: list}.
    Does not modify the input.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if df is None or df.empty:
        return {'valid': False, 'errors': ['DataFrame is None or empty.'], 'warnings': []}

    if len(df.columns) < 3:
        errors.append(f'Expected at least 3 columns, found {len(df.columns)}.')

    # Check for completely empty rows
    empty_rows = df.isna().all(axis=1).sum()
    if empty_rows > 0:
        warnings.append(f'{empty_rows} completely empty row(s) will be dropped.')

    # Check for duplicate rows
    dupes = df.duplicated().sum()
    if dupes > 0:
        warnings.append(f'{dupes} duplicate row(s) detected.')

    # Check that at least one pass_fail-like column exists
    pf_candidates = {'pass_fail', 'status', 'result', 'state'}
    if not pf_candidates.intersection({str(c).strip().lower() for c in df.columns}):
        errors.append('No pass/fail column found (expected one of: pass_fail, status, result, state).')

    return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}


def standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes common ICT/FCT CSV schema variants into the CircuitMind
    standard schema (alias-based column mapping, not an arbitrary-format
    parser).
    """
    
    # 1. Normalize Column Names
    col_mapping = {
        'board_id': ['board_id', 'serial', 'sn', 'board_sn', 'id'],
        'test_step': ['test_step', 'test_name', 'step', 'test'],
        'measured_value': ['measured_value', 'measured', 'val', 'reading', 'value'],
        'expected_min': ['expected_min', 'min_val', 'low_limit', 'll'],
        'expected_max': ['expected_max', 'max_val', 'high_limit', 'hl'],
        'pass_fail': ['pass_fail', 'status', 'result', 'state'],
        'error_code': ['error_code', 'error', 'code', 'fail_code'],
        'unit': ['unit', 'units', 'measure_unit']
    }
    
    # Lowercase and strip existing columns
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    new_cols = {}
    for standard_col, variants in col_mapping.items():
        for variant in variants:
            if variant in df.columns:
                new_cols[variant] = standard_col
                break
                
    df = df.rename(columns=new_cols)
    
    # Ensure required columns exist
    required = ['test_step', 'measured_value', 'expected_min', 'expected_max', 'pass_fail']
    for req in required:
        if req not in df.columns:
            raise ValueError(f"Missing required column (or known variant): {req}")

    for optional in ['error_code', 'unit']:
        if optional not in df.columns:
            df[optional] = ''

    if 'board_id' not in df.columns:
        df['board_id'] = 'UPLOAD_001'
    elif df['board_id'].isna().all() or (df['board_id'].astype(str).str.strip() == '').all():
        df['board_id'] = 'UPLOAD_001'
                
    # 2. Normalize Values
    df['pass_fail'] = df['pass_fail'].astype(str).str.strip().str.upper()
    
    # Map common string and numeric pass/fail conventions to the canonical pair.
    pass_variants = ['PASS', 'P', 'OK', '1', 'TRUE']
    fail_variants = ['FAIL', 'F', 'NG', '0', 'FALSE']
    
    df.loc[df['pass_fail'].isin(pass_variants), 'pass_fail'] = 'PASS'
    df.loc[df['pass_fail'].isin(fail_variants), 'pass_fail'] = 'FAIL'
        
    # Convert numerical columns
    for num_col in ['measured_value', 'expected_min', 'expected_max']:
        df[num_col] = pd.to_numeric(df[num_col], errors='coerce')

    # A test can also be ABORTED, SKIPPED, NOT_EXECUTED or INVALID. None of
    # these are failures: the engine only ever treats 'FAIL' as a failure, and
    # the test-integrity layer reports the rest explicitly. Anything else
    # (typo, foreign convention) is still rejected loudly.
    non_result_statuses = {'ABORT', 'NOT_EXECUTED', 'SKIPPED', 'INVALID', 'UNKNOWN'}
    statuses = set(df['pass_fail'].dropna().astype(str).unique())
    invalid_statuses = statuses - {'PASS', 'FAIL'} - non_result_statuses
    if invalid_statuses:
        raise ValueError(f"Unsupported pass/fail values: {', '.join(sorted(invalid_statuses))}")
        
    return df
