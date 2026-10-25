import networkx as nx
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class TopologyDAG:
    """
    Layer 2: Causal Hypothesis Engine.
    Models the circuit as three explicit graph layers:

    Layer A — Electrical connectivity (component <-> net via pin roles):
        answers "what is physically connected?"

    Layer B — Functional dependency (component -> dependent components):
        answers "what function depends on what?" A fault in an upstream
        component can disable everything that depends on it, even without a
        direct wire.

    Layer C — Test observability (test step -> net/component/function):
        answers "what does this test actually tell us?"

    The directed DAG (Layer A) drives primary/cascade classification; the
    functional layer drives mechanism-based expected-vs-observed reasoning;
    the observability layer maps tests to the elements they observe.
    """

    def __init__(
        self,
        nets_path: str = None,
        comps_path: str = None,
        functional_path: str = None,
        observability_path: str = None,
    ):
        nets_path = nets_path or str(DATA_DIR / 'net_connections.csv')
        comps_path = comps_path or str(DATA_DIR / 'components.csv')
        functional_path = functional_path or str(DATA_DIR / 'functional_dependencies.csv')
        observability_path = observability_path or str(DATA_DIR / 'test_observability.csv')

        self.G = nx.DiGraph()
        self.F = nx.DiGraph()
        self.observability: Dict[str, Dict[str, str]] = {}
        self._build_graph(nets_path, comps_path)
        self._build_functional(functional_path)
        self._build_observability(observability_path)

    def _build_graph(self, nets_path: str, comps_path: str):
        df_nets = pd.read_csv(nets_path)
        df_comps = pd.read_csv(comps_path).set_index('refdes')

        # Add components as nodes
        for refdes, row in df_comps.iterrows():
            self.G.add_node(refdes, type='component', cat=row['cat'], critical=row['critical'])

        # Add nets as nodes
        unique_nets = df_nets['net_name'].unique()
        for net in unique_nets:
            self.G.add_node(net, type='net')

        # Add edges based on pin roles (Power flow, signal flow)
        for _, row in df_nets.iterrows():
            ref = row['refdes']
            net = row['net_name']
            role = row['pin_role']

            if role in ['POWER_OUT', 'SIGNAL_OUT', 'SOURCE']:
                self.G.add_edge(ref, net)
            elif role in ['POWER_IN', 'SIGNAL_IN', 'PASSIVE']:
                self.G.add_edge(net, ref)
            elif role == 'BIDIR':
                # For simplified DAG causal tracing, treat bidir as dependent on the net
                self.G.add_edge(net, ref)

    def _build_functional(self, functional_path: str):
        """Functional dependency graph: edge cause -> dependent (component)."""
        try:
            df = pd.read_csv(functional_path)
        except FileNotFoundError:
            return
        for _, row in df.iterrows():
            component = str(row['component']).strip()
            depends_on = str(row['depends_on']).strip()
            if component and depends_on:
                self.F.add_edge(depends_on, component, kind=str(row.get('kind', 'DATA')))

    def _build_observability(self, observability_path: str):
        """Test observability: test_step -> {net, component, function}."""
        try:
            df = pd.read_csv(observability_path)
        except FileNotFoundError:
            return
        for _, row in df.iterrows():
            step = str(row['test_step']).strip()
            self.observability[step] = {
                'net': str(row.get('observes_net', '')).strip(),
                'component': str(row.get('observes_component', '')).strip(),
                'function': str(row.get('observes_function', '')).strip(),
            }

    def analyze_cascades(self, failed_nets: List[str]) -> Dict:
        """
        Takes a list of failed nets and determines which are primary (root) vs secondary (cascade).
        """
        primary_nets = set(failed_nets)
        secondary_nets = set()

        # A net is secondary if it can be reached from another failed net downstream
        for src in failed_nets:
            for dst in failed_nets:
                if src != dst and src in self.G and dst in self.G:
                    if nx.has_path(self.G, src, dst):
                        secondary_nets.add(dst)
                        if dst in primary_nets:
                            primary_nets.remove(dst)

        # Find suspect components (upstream of primary nets)
        primary_suspects = set()
        for net in primary_nets:
            if net in self.G:
                primary_suspects.update(self.get_upstream_components(net))

        cycles = list(nx.simple_cycles(self.G)) if not nx.is_directed_acyclic_graph(self.G) else []
        causal_paths = []
        for src in sorted(set(failed_nets)):
            for dst in sorted(set(failed_nets)):
                if src == dst or src not in self.G or dst not in self.G:
                    continue
                if nx.has_path(self.G, src, dst):
                    try:
                        path = next(nx.all_simple_paths(self.G, src, dst, cutoff=12))
                    except StopIteration:
                        continue
                    causal_paths.append({'source_net': src, 'symptom_net': dst, 'path': path})

        return {
            'primary_nets': list(primary_nets),
            'cascade_nets': list(secondary_nets),
            'primary_suspects': list(primary_suspects),
            'causal_paths': causal_paths,
            'dependency_graph_is_dag': len(cycles) == 0,
            'cycles': cycles
        }

    def get_upstream_components(self, net: str) -> List[str]:
        """Get all components that feed into this net"""
        if net not in self.G:
            return []
        return sorted(
            node for node in nx.ancestors(self.G, net)
            if self.G.nodes[node].get('type') == 'component'
        )

    def get_downstream_nets(self, refdes: str) -> Set[str]:
        """All nets reachable downstream from a component (its outputs and
        everything they cascade into). Used for counterfactual coverage: if this
        component were faulty, these nets would be affected."""
        if refdes not in self.G:
            return set()
        return {
            node for node in nx.descendants(self.G, refdes)
            if self.G.nodes[node].get('type') == 'net'
        }

    # ------------------------------------------------------------------
    # Layer B — Functional dependency
    # ------------------------------------------------------------------
    def get_functional_downstream_components(self, refdes: str) -> Set[str]:
        """All components that functionally depend (directly or transitively)
        on ``refdes`` — i.e. would be affected by a fault in it."""
        if refdes not in self.F:
            return set()
        return set(nx.descendants(self.F, refdes))

    def get_functional_downstream_nets(self, refdes: str, comps: pd.DataFrame = None) -> Set[str]:
        """Nets of the functional downstream dependents (plus the component's own net)."""
        downstream = self.get_functional_downstream_components(refdes)
        if not downstream:
            return set()
        if comps is None:
            return set()  # caller should pass the BOM; nets resolved upstream
        nets = set()
        for comp in downstream:
            if comp in comps.index:
                nets.add(str(comps.loc[comp, 'net']))
        return nets

    def functional_chain(self, source: str, comps: pd.DataFrame = None) -> List[Dict]:
        """Human-readable functional dependency chains rooted at ``source``."""
        if source not in self.F:
            return []
        chains = []
        for target in sorted(nx.descendants(self.F, source)):
            try:
                path = nx.shortest_path(self.F, source, target)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            chains.append({
                'source': source,
                'target': target,
                'path': path,
                'kind': self.F.edges[(path[-2], path[-1])].get('kind', 'DATA') if len(path) > 1 else 'DATA',
            })
        return chains

    # ------------------------------------------------------------------
    # Layer C — Test observability
    # ------------------------------------------------------------------
    def test_observability(self, test_step: str) -> Dict[str, str]:
        """What a test observes: {net, component, function} (empty dict if unmapped)."""
        return self.observability.get(test_step, {})

    def analyze_observability(self, failed_tests: List[Dict]) -> Dict:
        """Which functions/components/nets are observed failing by the failed tests."""
        functions = {}
        components = {}
        for test in failed_tests:
            step = test.get('test_step', '')
            info = self.test_observability(step)
            fn = info.get('function', '')
            comp = info.get('component', '')
            if fn:
                functions[fn] = functions.get(fn, 0) + 1
            if comp:
                components[comp] = components.get(comp, 0) + 1
        return {
            'failed_functions': sorted(functions, key=lambda f: -functions[f]),
            'observed_components': sorted(components, key=lambda c: -components[c]),
            'unmapped_tests': [
                t['test_step'] for t in failed_tests
                if not self.test_observability(t.get('test_step', ''))
            ],
        }
