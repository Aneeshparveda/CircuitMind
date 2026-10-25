"""Version identity for CircuitMind's engine and knowledge assets.

Every report records these so any diagnosis can be reproduced against the exact
engine + data + policy combination that produced it.
"""

ENGINE_VERSION = "2.0.0"
DATA_VERSION = "2026-08-11"
POLICY_VERSION = "evidence-policy-v1"
TOPOLOGY_VERSION = "three-layer-v1"
RETRIEVAL_VERSION = "tfidf-v1"
BENCHMARK_VERSION = "benchmark-v1"

VERSIONS = {
    "engine": ENGINE_VERSION,
    "data": DATA_VERSION,
    "policy": POLICY_VERSION,
    "topology": TOPOLOGY_VERSION,
    "retrieval": RETRIEVAL_VERSION,
    "benchmark": BENCHMARK_VERSION,
}
