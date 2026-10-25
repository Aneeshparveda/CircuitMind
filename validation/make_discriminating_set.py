"""Generate the DISCRIMINATING benchmark — the proof that the evidence
architecture beats trivial failure-pattern matching.

The audit's most damaging question: "your 88% equals a simple Jaccard
classifier on the failed-test pattern." That is true on the instance holdout,
because the 15 generated families are separable by failed-step pattern alone.

This set inverts the test: every board in a cluster has the SAME failed-test
set, but a DIFFERENT root cause. The only evidence that separates them is what
the log MEASURES — error code (VAL vs OPN vs SHT vs FNC) and deviation
magnitude — plus mechanism (expected blast radius). A pattern matcher can only
guess; the fusion should be able to separate.

Clusters (deterministic; boards are never seen by the shipped memory or
pattern signals — they live only under validation/discriminating/):

  A. {TEST_5V_RAIL}               U3 (VAL, hard drop) / L1 (OPN, 0V) / C1 (VAL, marginal)
  B. {3V3 + digital cascade}      U2 (VAL, soft) / C2 (SHT, hard short)
  C. {TEST_I2C_BUS}               U6 (SHT) / R1 (FNC)
  D. {TEST_RF_POWER}              A1 (VAL, low dBm) / U4 (FNC, none)

Run: python3 validation/make_discriminating_set.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.generate_synthetic import EXPECTED  # noqa: E402

# (board_id, root, {step: (measured, error_code)})
CLUSTERS = [
    # A — single 5V rail failure
    ('DISC_A_U3_01', 'U3', {'TEST_5V_RAIL': (0.8, 'VAL')}),
    ('DISC_A_U3_02', 'U3', {'TEST_5V_RAIL': (1.0, 'VAL')}),
    ('DISC_A_U3_03', 'U3', {'TEST_5V_RAIL': (1.2, 'VAL')}),
    ('DISC_A_L1_01', 'L1', {'TEST_5V_RAIL': (0.05, 'OPN')}),
    ('DISC_A_L1_02', 'L1', {'TEST_5V_RAIL': (0.10, 'OPN')}),
    ('DISC_A_L1_03', 'L1', {'TEST_5V_RAIL': (0.15, 'OPN')}),
    ('DISC_A_C1_01', 'C1', {'TEST_5V_RAIL': (4.35, 'VAL')}),
    ('DISC_A_C1_02', 'C1', {'TEST_5V_RAIL': (4.45, 'VAL')}),
    ('DISC_A_C1_03', 'C1', {'TEST_5V_RAIL': (4.55, 'VAL')}),
    # B — 3V3 rail + digital cascade
    ('DISC_B_U2_01', 'U2', {'TEST_3V3_RAIL': (0.6, 'VAL'),
                            'TEST_MCU_BOOT': (0, 'FNC'), 'TEST_SPI_FLASH': (0, 'FNC'),
                            'TEST_WIFI_ENUM': (0, 'FNC'), 'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_B_U2_02', 'U2', {'TEST_3V3_RAIL': (0.8, 'VAL'),
                            'TEST_MCU_BOOT': (0, 'FNC'), 'TEST_SPI_FLASH': (0, 'FNC'),
                            'TEST_WIFI_ENUM': (0, 'FNC'), 'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_B_U2_03', 'U2', {'TEST_3V3_RAIL': (1.0, 'VAL'),
                            'TEST_MCU_BOOT': (0, 'FNC'), 'TEST_SPI_FLASH': (0, 'FNC'),
                            'TEST_WIFI_ENUM': (0, 'FNC'), 'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_B_C2_01', 'C2', {'TEST_3V3_RAIL': (0.15, 'SHT'),
                            'TEST_MCU_BOOT': (0, 'FNC'), 'TEST_SPI_FLASH': (0, 'FNC'),
                            'TEST_WIFI_ENUM': (0, 'FNC'), 'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_B_C2_02', 'C2', {'TEST_3V3_RAIL': (0.25, 'SHT'),
                            'TEST_MCU_BOOT': (0, 'FNC'), 'TEST_SPI_FLASH': (0, 'FNC'),
                            'TEST_WIFI_ENUM': (0, 'FNC'), 'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_B_C2_03', 'C2', {'TEST_3V3_RAIL': (0.35, 'SHT'),
                            'TEST_MCU_BOOT': (0, 'FNC'), 'TEST_SPI_FLASH': (0, 'FNC'),
                            'TEST_WIFI_ENUM': (0, 'FNC'), 'TEST_I2C_BUS': (0, 'FNC')}),
    # C — I2C bus
    ('DISC_C_U6_01', 'U6', {'TEST_I2C_BUS': (0, 'SHT')}),
    ('DISC_C_U6_02', 'U6', {'TEST_I2C_BUS': (0, 'SHT')}),
    ('DISC_C_U6_03', 'U6', {'TEST_I2C_BUS': (0, 'SHT')}),
    ('DISC_C_R1_01', 'R1', {'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_C_R1_02', 'R1', {'TEST_I2C_BUS': (0, 'FNC')}),
    ('DISC_C_R1_03', 'R1', {'TEST_I2C_BUS': (0, 'FNC')}),
    # D — RF power
    ('DISC_D_A1_01', 'A1', {'TEST_RF_POWER': (2.0, 'VAL')}),
    ('DISC_D_A1_02', 'A1', {'TEST_RF_POWER': (3.5, 'VAL')}),
    ('DISC_D_A1_03', 'A1', {'TEST_RF_POWER': (5.0, 'VAL')}),
    ('DISC_D_U4_01', 'U4', {'TEST_RF_POWER': (0, 'FNC')}),
    ('DISC_D_U4_02', 'U4', {'TEST_RF_POWER': (0, 'FNC')}),
    ('DISC_D_U4_03', 'U4', {'TEST_RF_POWER': (0, 'FNC')}),
]

# Nominal passing readings (midpoint of the expected range, slightly varied).
NOMINAL = {
    'TEST_VBUS': 5.0, 'TEST_FUSE': 4.95, 'TEST_5V_RAIL': 5.0, 'TEST_3V3_RAIL': 3.3,
    'TEST_MCU_BOOT': 1, 'TEST_SPI_FLASH': 1, 'TEST_WIFI_ENUM': 1, 'TEST_RF_POWER': 17.5,
    'TEST_I2C_BUS': 1, 'TEST_THERMISTOR': 2.25, 'TEST_MOTOR_PWM': 1,
}


def make_discriminating_set():
    logs = []
    truth = []
    for board_id, root, failing in CLUSTERS:
        truth.append({'board_id': board_id, 'root_cause': root,
                      'scenario': f'DISCRIMINATING cluster {board_id.split("_")[1]}', 'split': 'discriminating'})
        for step, (ex_min, ex_max, unit) in EXPECTED.items():
            if step in failing:
                meas, err = failing[step]
                logs.append({'board_id': board_id, 'test_step': step,
                             'measured_value': meas, 'expected_min': ex_min,
                             'expected_max': ex_max, 'unit': unit,
                             'pass_fail': 'FAIL', 'error_code': err})
            else:
                logs.append({'board_id': board_id, 'test_step': step,
                             'measured_value': NOMINAL[step], 'expected_min': ex_min,
                             'expected_max': ex_max, 'unit': unit,
                             'pass_fail': 'PASS', 'error_code': ''})
    out_dir = ROOT / 'validation' / 'discriminating'
    out_dir.mkdir(exist_ok=True)
    pd.DataFrame(logs).to_csv(out_dir / 'logs.csv', index=False)
    pd.DataFrame(truth).to_csv(out_dir / 'ground_truth.csv', index=False)
    print(f"Discriminating set written: {len(truth)} boards across "
          f"{len({b[1] for b in CLUSTERS})} root causes, {len({b[0].split('_')[1] for b in CLUSTERS})} clusters.")


if __name__ == '__main__':
    make_discriminating_set()
