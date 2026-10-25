import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from typing import Dict, List, Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Deviation buckets mirror SignatureExtractor's formula: boolean/functional
# failures score 3.0, then the magnitude is rounded onto a 0-5 scale so a
# severe deviation token (dev5) never ranks the same as a mild one (dev1).
def _deviation_score(measured, expected_min, expected_max) -> float:
    if pd.isna(expected_min) or pd.isna(expected_max) or expected_min == expected_max:
        return 3.0
    midpoint = (expected_max + expected_min) / 2.0
    half_range = (expected_max - expected_min) / 2.0
    if half_range == 0 or pd.isna(measured):
        return 3.0
    return float(abs(measured - midpoint) / half_range)


def _deviation_token(deviation: float) -> str:
    return f"dev{int(round(min(max(deviation, 0.0), 5.0)))}"


class SemanticMemory:
    """
    Layer 3: Searches historical cases using TF-IDF.

    The retrieval query matches on failed test steps, the primary domain,
    deviation magnitude, and error codes. Signal tokens for each historical
    case are derived from the built-in test logs (the only place severity and
    error-code data live), so a severe deviation is never ranked the same as
    a mild one. Includes PCA projection for Pattern Space visualization.
    """

    def __init__(self, history_path: str = None, logs_path: str = None):
        history_path = history_path or str(DATA_DIR / 'repair_history.csv')
        logs_path = logs_path or str(DATA_DIR / 'test_logs.csv')
        self.df = pd.read_csv(history_path)
        self.vectorizer = TfidfVectorizer(stop_words='english')

        # Per failure-pattern severity/error signals, derived deterministically
        # from the built-in test logs.
        self.pattern_signals = self._derive_pattern_signals(logs_path)

        # Build memory vectors from symptoms + failed steps + signal tokens
        self.corpus = [
            f"{row['symptom_text']} {row['failed_steps']} {self._signal_tokens(row['failed_steps'])}"
            for _, row in self.df.iterrows()
        ]
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

        # Compute PCA for 2D Pattern Space visualization
        # We use PCA instead of t-SNE because it's deterministic and allows transforming new points easily
        self.pca = PCA(n_components=2, random_state=42)
        if self.tfidf_matrix.shape[0] > 0:
            self.pca_coords = self.pca.fit_transform(self.tfidf_matrix.toarray())
            self.df['pca_x'] = self.pca_coords[:, 0]
            self.df['pca_y'] = self.pca_coords[:, 1]

    def _derive_pattern_signals(self, logs_path: str) -> Dict[frozenset, Dict[str, Any]]:
        """Aggregate deviation magnitude and error codes per failed-step pattern."""
        try:
            logs = pd.read_csv(logs_path)
        except FileNotFoundError:
            return {}
        failed = logs[logs['pass_fail'].astype(str).str.strip().str.upper() == 'FAIL'].copy()
        if failed.empty:
            return {}

        deviations = []
        for _, row in failed.iterrows():
            deviations.append(_deviation_score(row['measured_value'], row['expected_min'], row['expected_max']))
        failed['deviation'] = deviations

        signals: Dict[frozenset, Dict[str, Any]] = {}
        for _, group in failed.groupby('board_id'):
            pattern = frozenset(group['test_step'].astype(str).str.strip())
            entry = signals.setdefault(pattern, {'dev_by_step': {}, 'error_codes': set()})
            for _, row in group.iterrows():
                step = str(row['test_step']).strip()
                entry['dev_by_step'].setdefault(step, []).append(float(row['deviation']))
                code = str(row['error_code']).strip() if not pd.isna(row['error_code']) else ''
                if code:
                    entry['error_codes'].add(code)

        for entry in signals.values():
            entry['dev_by_step'] = {
                step: float(np.mean(values))
                for step, values in entry['dev_by_step'].items()
            }
        return signals

    def _signal_tokens(self, failed_steps: str) -> str:
        """Signal tokens for one historical case, derived from its failed-step pattern."""
        if not isinstance(failed_steps, str) or not failed_steps.strip():
            return ''
        pattern = frozenset(step.strip() for step in failed_steps.split('|') if step.strip())
        entry = self.pattern_signals.get(pattern)
        if not entry:
            return ''
        tokens = [_deviation_token(entry['dev_by_step'][step]) for step in sorted(entry['dev_by_step'])]
        tokens.extend(f"err{code}" for code in sorted(entry['error_codes']))
        return ' '.join(tokens)

    @staticmethod
    def _query_signal_tokens(signature: Dict[str, Any]) -> str:
        """Signal tokens for the board under test, computed from its own failures."""
        tokens = []
        for test in signature['failed_tests']:
            tokens.append(_deviation_token(float(test['deviation'])))
            code = str(test.get('error_code') or '').strip()
            if code:
                tokens.append(f"err{code}")
        return ' '.join(tokens)

    def search(self, signature: Dict[str, Any], top_k: int = 5, extra_text: str = "") -> Dict:
        """
        Searches historical cases given the current failure signature.

        ``extra_text`` is optional session free text (for example repair notes)
        that is folded into the query so typed observations influence retrieval.
        """
        if not signature['failed_tests']:
            return {'matches': [], 'pca_point': [0, 0]}

        # Construct query from failed tests, primary domain, severity/error
        # signals, and any session repair notes.
        query_parts = [
            ' '.join(t['test_step'] for t in signature['failed_tests']),
            signature['primary_domain'],
            self._query_signal_tokens(signature),
        ]
        if extra_text and extra_text.strip():
            query_parts.append(extra_text.strip())
        query_str = ' '.join(part for part in query_parts if part)

        query_vec = self.vectorizer.transform([query_str])

        # Calculate Cosine Similarity
        sims = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Get top K indices
        top_idx = sims.argsort()[-top_k:][::-1]

        matches = []
        for idx in top_idx:
            if sims[idx] > 0:  # Only return actual matches
                match = self.df.iloc[idx].to_dict()
                match['similarity'] = float(sims[idx] * 100)  # Convert to percentage
                matches.append(match)

        # Project current query into PCA space for the visualization
        query_pca = [0, 0]
        if hasattr(self, 'pca'):
            try:
                query_pca_raw = self.pca.transform(query_vec.toarray())[0]
                query_pca = [float(query_pca_raw[0]), float(query_pca_raw[1])]
            except Exception:
                pass

        # Full pattern-space coordinates so the UI can render the entire
        # history corpus around the live board's query point.
        cases = []
        if hasattr(self, 'df') and 'pca_x' in self.df.columns:
            for _, row in self.df.iterrows():
                cases.append({
                    'repair_id': str(row['repair_id']),
                    'root_cause_component': str(row['root_cause_component']),
                    'x': float(row['pca_x']),
                    'y': float(row['pca_y']),
                })

        return {
            'matches': matches,
            'pca_point': query_pca,
            'cases': cases
        }
