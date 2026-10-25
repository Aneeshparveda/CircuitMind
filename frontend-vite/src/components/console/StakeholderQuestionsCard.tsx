export default function StakeholderQuestionsCard() {
  const faqs = [
    { q: 'Why should government fund this?', a: 'Reduces e-waste, improves first-pass yield, preserves expert knowledge, enables MSMEs with offline/on-prem deployment. Supports Make-in-India electronics manufacturing scale-up. See Gov Impact card above.' },
    { q: 'What\'s the subscription plan?', a: 'Pilot (4–6 weeks one-time), Pro (annual per-line license), Enterprise (MES connectors, RBAC, SLA). See Pricing card above.' },
    { q: 'How do we generate revenue?', a: 'Annual license + integration services + support + enterprise connectors. The diagnostic sidecar model means we complement, not replace, existing MES investments.' },
    { q: 'How is this different from Siemens/Keysight/Aegis?', a: 'We don\'t replace MES — we add root-cause evidence chains, counterfactual reasoning, fixture attribution, and OOD abstention that those platforms lack. See Competitive Landscape card above.' },
    { q: 'How do you know it\'s fixture vs board?', a: 'The fleet tester analysis compares failure rates across fixtures running the same test. If one fixture has 100% failure while peers have 0%, it\'s the fixture. See the Tester-Anomaly demo case.' },
    { q: 'What data do you need from a factory?', a: 'Minimum: board_id, test_step, pass_fail, measured_value, expected range, error_code. Optional high-value: timestamp, station_id, fixture_id, board_revision. See Integration card above.' },
    { q: 'What are the limitations?', a: 'Evidence strength, not calibrated probability. Requires physical verification. Best with historical repair memory overlap. Simplified topology in MVP. See Limitations card above.' },
  ];

  return (
    <div className="exec-card bento-tilt">
      {faqs.map((f, i) => (
        <details key={i} className="faq-item">
          <summary>{f.q}</summary>
          <p>{f.a}</p>
        </details>
      ))}
    </div>
  );
}
