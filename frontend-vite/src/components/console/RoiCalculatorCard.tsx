import { useState } from 'react';

const fmtINR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v);

export default function RoiCalculatorCard() {
  const [boardsPerDay, setBoardsPerDay] = useState(500);
  const [failRatePct, setFailRatePct] = useState(3);
  const [debugMinsCurrent, setDebugMinsCurrent] = useState(45);
  const [debugMinsWith, setDebugMinsWith] = useState(12);
  const [engineerCostPerHour, setEngineerCostPerHour] = useState(1200);
  const [falseReworkRatePct, setFalseReworkRatePct] = useState(20);
  const [falseReworkCost, setFalseReworkCost] = useState(1500);
  const [falseReworkReductionPct, setFalseReworkReductionPct] = useState(60);
  const [workingDaysPerYear, setWorkingDaysPerYear] = useState(250);

  const failedBoardsPerDay = boardsPerDay * (failRatePct / 100);
  const debugCostCurrent = failedBoardsPerDay * (debugMinsCurrent / 60) * engineerCostPerHour;
  const debugCostWith = failedBoardsPerDay * (debugMinsWith / 60) * engineerCostPerHour;
  const falseReworkCostCurrent = failedBoardsPerDay * (falseReworkRatePct / 100) * falseReworkCost;
  const falseReworkCostWith = falseReworkCostCurrent * (1 - falseReworkReductionPct / 100);
  const totalCurrent = debugCostCurrent + falseReworkCostCurrent;
  const totalWith = debugCostWith + falseReworkCostWith;
  const dailySavings = totalCurrent - totalWith;
  const annualSavings = dailySavings * workingDaysPerYear;

  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>ROI CALCULATOR</b><small>INTERACTIVE · ALL VALUES IN INR</small></div>
      <div className="roi-grid">
        <div className="roi-inputs">
          <label>Boards/day <input type="number" value={boardsPerDay} onChange={e => setBoardsPerDay(+e.target.value)} /></label>
          <label>Fail rate % <input type="number" value={failRatePct} onChange={e => setFailRatePct(+e.target.value)} /></label>
          <label>Debug min/board (current) <input type="number" value={debugMinsCurrent} onChange={e => setDebugMinsCurrent(+e.target.value)} /></label>
          <label>Debug min/board (with CM) <input type="number" value={debugMinsWith} onChange={e => setDebugMinsWith(+e.target.value)} /></label>
          <label>Engineer cost/hr (INR) <input type="number" value={engineerCostPerHour} onChange={e => setEngineerCostPerHour(+e.target.value)} /></label>
          <label>False rework rate % <input type="number" value={falseReworkRatePct} onChange={e => setFalseReworkRatePct(+e.target.value)} /></label>
          <label>False rework cost (INR) <input type="number" value={falseReworkCost} onChange={e => setFalseReworkCost(+e.target.value)} /></label>
          <label>False rework reduction % <input type="number" value={falseReworkReductionPct} onChange={e => setFalseReworkReductionPct(+e.target.value)} /></label>
          <label>Working days/year <input type="number" value={workingDaysPerYear} onChange={e => setWorkingDaysPerYear(+e.target.value)} /></label>
        </div>
        <div className="roi-outputs">
          <div className="roi-metric"><small>FAILED BOARDS / DAY</small><strong>{failedBoardsPerDay.toFixed(0)}</strong></div>
          <div className="roi-metric"><small>CURRENT COST / DAY</small><strong>{fmtINR(totalCurrent)}</strong></div>
          <div className="roi-metric roi-metric--with"><small>WITH CIRCUITMIND / DAY</small><strong>{fmtINR(totalWith)}</strong></div>
          <div className="roi-metric roi-metric--save"><small>DAILY SAVINGS</small><strong>{fmtINR(dailySavings)}</strong></div>
          <div className="roi-metric roi-metric--annual"><small>ANNUAL SAVINGS (ESTIMATE)</small><strong>{fmtINR(annualSavings)}</strong></div>
        </div>
      </div>
      <small style={{ display: 'block', marginTop: 12, color: '#5a7a80', fontSize: 10 }}>Estimates for demo. Actual savings depend on yield, process, and data quality.</small>
    </div>
  );
}
