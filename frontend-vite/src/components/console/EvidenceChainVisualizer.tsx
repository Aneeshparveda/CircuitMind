import './EvidenceChain.css';

interface ChainNode {
  stage: string;
  icon: string;
  label: string;
  detail: string;
  strength: 'strong' | 'moderate' | 'weak';
  accent: string;
}

function buildChain(report: any): ChainNode[] {
  const nodes: ChainNode[] = [];

  /* 1 — SYMPTOMS */
  const fails = report?.failed_tests ?? [];
  const failNames = fails.slice(0, 3).map((t: any) => t.test_step ?? t.id ?? '?');
  const failCount = fails.length || 1;
  nodes.push({
    stage: 'SYMPTOMS',
    icon: '🔍',
    label: `${failCount} Failing Test${failCount !== 1 ? 's' : ''}`,
    detail: failNames.length ? `${failNames.join(', ')}${fails.length > 3 ? ' …' : ''}` : 'Analyzing…',
    strength: failCount >= 3 ? 'strong' : failCount >= 1 ? 'moderate' : 'weak',
    accent: '#ff6b6b',
  });

  /* 2 — TOPOLOGY */
  const suspects = report?.suspects ?? [];
  const topSuspect = suspects[0];
  const cascade = report?.topology_cascade;
  const domainPath = cascade?.path ?? null;
  const topologyDetail = domainPath
    ? domainPath.join(' → ')
    : topSuspect
      ? `${topSuspect.refdes} / ${topSuspect.desc ?? 'power domain'}`
      : 'Topology graph constructed';
  nodes.push({
    stage: 'TOPOLOGY',
    icon: '⚡',
    label: 'Domain Cascade',
    detail: topologyDetail,
    strength: suspects.length >= 2 ? 'strong' : 'moderate',
    accent: '#8b949e',
  });

  /* 3 — COUNTERFACTUAL */
  const ec = topSuspect?.evidence_contributions ?? {};
  const totalEv = Object.values(ec).reduce((s: number, v: any) => s + (Number(v) || 0), 0) as number;
  const topScore = topSuspect?.score ?? 0;
  const cfDetail = totalEv > 0
    ? `${topSuspect.refdes} explains ${Math.round(topScore)}% · ${Object.keys(ec).length} evidence streams fused`
    : suspects.length > 1
      ? `${topSuspect.refdes} leads — ${suspects[1]?.refdes} rejected by counterfactual`
      : 'Counterfactual analysis complete';
  nodes.push({
    stage: 'COUNTERFACTUAL',
    icon: '⚖️',
    label: 'Counterfactual Test',
    detail: cfDetail,
    strength: topScore >= 60 ? 'strong' : topScore >= 40 ? 'moderate' : 'weak',
    accent: '#72dfe2',
  });

  /* 4 — PRECEDENT */
  const precedent = report?.precedent;
  const prevCount = precedent?.case_count ?? 0;
  const prevAction = precedent?.fix_action ?? precedent?.action ?? null;
  const prevDetail = prevCount > 0
    ? `${prevCount} prior case${prevCount !== 1 ? 's' : ''}${prevAction ? ` — ${prevAction}` : ''}`
    : 'No close historical match found';
  nodes.push({
    stage: 'PRECEDENT',
    icon: '📚',
    label: 'Repair Memory',
    detail: prevDetail,
    strength: prevCount >= 3 ? 'strong' : prevCount >= 1 ? 'moderate' : 'weak',
    accent: '#5ddb6d',
  });

  /* 5 — ACTION */
  const nba = report?.next_best_action;
  const actionDetail = nba
    ? typeof nba === 'string'
      ? nba
      : nba.action ?? nba.description ?? JSON.stringify(nba)
    : topSuspect
      ? `Verify ${topSuspect.refdes} before board-level rework`
      : 'Awaiting analysis';
  nodes.push({
    stage: 'ACTION',
    icon: '🛠️',
    label: 'Next Best Test',
    detail: actionDetail,
    strength: 'strong',
    accent: '#f6cb85',
  });

  return nodes;
}

function Connector() {
  return (
    <div className="chain-connector">
      <div className="chain-connector__line">
        <div className="chain-connector__pulse" />
      </div>
      <div className="chain-connector__arrow" />
    </div>
  );
}

export default function EvidenceChainVisualizer({ report }: { report?: any }) {
  const nodes = report ? buildChain(report) : [];

  if (!report || nodes.length === 0) {
    return (
      <div className="evidence-chain evidence-chain--empty">
        <span className="chain-empty-text">Load a case to see the reasoning chain reconstructed step-by-step.</span>
      </div>
    );
  }

  return (
    <div className="evidence-chain">
      {nodes.map((node, i) => (
        <div key={node.stage} style={{ display: 'flex', alignItems: 'center' }}>
          {i > 0 && <Connector />}
          <div className={`chain-node chain-node--${node.strength}`}>
            <span className="chain-node__icon">{node.icon}</span>
            <span className="chain-node__stage">{node.stage}</span>
            <span className="chain-node__label">{node.label}</span>
            <span className="chain-node__detail">{node.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
