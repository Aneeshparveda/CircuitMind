import pandas as pd
import numpy as np
import os
import random
import uuid

RANDOM_SEED = 42

# Fault Scenarios (15 realistic failures) — module level so downstream tools
# (e.g. the reserve-set generator) share the exact same scenarios.
SCENARIOS = [
    {'name': 'U3 Buck Failure', 'root': 'U3', 'tests': {'TEST_5V_RAIL': (0.5, 1.5, 'VAL'), 'TEST_3V3_RAIL': (0.1, 0.5, 'VAL'), 'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC'), 'TEST_MOTOR_PWM': (0, 0, 'FNC')}},
    {'name': 'L1 Open', 'root': 'L1', 'tests': {'TEST_5V_RAIL': (0, 0.2, 'OPN'), 'TEST_3V3_RAIL': (0, 0.1, 'OPN'), 'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC'), 'TEST_MOTOR_PWM': (0, 0, 'FNC')}},
    {'name': 'F1 Blown', 'root': 'F1', 'tests': {'TEST_FUSE': (0, 0.2, 'OPN'), 'TEST_5V_RAIL': (0, 0, 'VAL'), 'TEST_3V3_RAIL': (0, 0, 'VAL'), 'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC'), 'TEST_MOTOR_PWM': (0, 0, 'FNC')}},
    {'name': 'U2 LDO Failure', 'root': 'U2', 'tests': {'TEST_3V3_RAIL': (0.5, 1.2, 'VAL'), 'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC')}},
    {'name': 'U1 MCU Dead', 'root': 'U1', 'tests': {'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC'), 'TEST_MOTOR_PWM': (0, 0, 'FNC')}},
    {'name': 'U5 SPI Flash Open', 'root': 'U5', 'tests': {'TEST_SPI_FLASH': (0, 0, 'OPN')}},
    {'name': 'U4 WiFi Dead', 'root': 'U4', 'tests': {'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC')}},
    {'name': 'A1 Antenna Disconnected', 'root': 'A1', 'tests': {'TEST_RF_POWER': (0, 5, 'VAL')}},
    {'name': 'I2C Bus Short', 'root': 'U6', 'tests': {'TEST_I2C_BUS': (0, 0, 'SHT')}},
    {'name': 'R1 Pullup Open', 'root': 'R1', 'tests': {'TEST_I2C_BUS': (0, 0, 'FNC')}},
    {'name': 'R12 Thermistor Open', 'root': 'R12', 'tests': {'TEST_THERMISTOR': (0, 0.1, 'OPN')}},
    {'name': 'Q1 MOSFET Short', 'root': 'Q1', 'tests': {'TEST_MOTOR_PWM': (12, 12, 'SHT')}},
    {'name': 'C1 Bulk Cap Open', 'root': 'C1', 'tests': {'TEST_5V_RAIL': (4.2, 4.6, 'VAL'), 'TEST_MOTOR_PWM': (0, 0, 'FNC')}},
    {'name': 'C2 Decoupling Short', 'root': 'C2', 'tests': {'TEST_3V3_RAIL': (0.1, 0.4, 'SHT'), 'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC')}},
    {'name': 'J1 USB Short', 'root': 'J1', 'tests': {'TEST_VBUS': (0, 1.0, 'SHT'), 'TEST_FUSE': (0, 0, 'VAL'), 'TEST_5V_RAIL': (0, 0, 'VAL'), 'TEST_3V3_RAIL': (0, 0, 'VAL'), 'TEST_MCU_BOOT': (0, 0, 'FNC'), 'TEST_SPI_FLASH': (0, 0, 'FNC'), 'TEST_WIFI_ENUM': (0, 0, 'FNC'), 'TEST_RF_POWER': (0, 0, 'FNC'), 'TEST_I2C_BUS': (0, 0, 'FNC'), 'TEST_MOTOR_PWM': (0, 0, 'FNC')}}
]

# Normal expected values for tests (module level for reuse).
EXPECTED = {
    'TEST_VBUS': (4.75, 5.25, 'V'),
    'TEST_FUSE': (4.70, 5.20, 'V'),
    'TEST_5V_RAIL': (4.8, 5.2, 'V'),
    'TEST_3V3_RAIL': (3.2, 3.4, 'V'),
    'TEST_MCU_BOOT': (1, 1, 'bool'),
    'TEST_SPI_FLASH': (1, 1, 'bool'),
    'TEST_WIFI_ENUM': (1, 1, 'bool'),
    'TEST_RF_POWER': (15, 20, 'dBm'),
    'TEST_I2C_BUS': (1, 1, 'bool'),
    'TEST_THERMISTOR': (2.0, 2.5, 'V'),
    'TEST_MOTOR_PWM': (1, 1, 'bool')
}


def generate_all_data():
    """Generates all 5 synthetic CSVs for CircuitMind"""
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    print("Generating Synthetic Data...")
    
    os.makedirs('data', exist_ok=True)
    os.makedirs('validation', exist_ok=True)
    
    # 1. Components BOM
    components = [
        # POWER
        {'refdes': 'J1', 'desc': 'USB-C Connector', 'cat': 'Connector', 'net': 'VBUS_5V', 'critical': True, 'x': 10, 'y': 50},
        {'refdes': 'F1', 'desc': 'PTC Fuse 2A', 'cat': 'Protection', 'net': 'VBUS_5V', 'critical': True, 'x': 20, 'y': 50},
        {'refdes': 'U3', 'desc': 'TPS54331 Buck', 'cat': 'IC', 'net': 'SYS_5V', 'critical': True, 'x': 30, 'y': 50},
        {'refdes': 'L1', 'desc': '4.7uH Inductor', 'cat': 'Inductor', 'net': 'SYS_5V', 'critical': True, 'x': 40, 'y': 50},
        {'refdes': 'C1', 'desc': '22uF Cap', 'cat': 'Capacitor', 'net': 'SYS_5V', 'critical': False, 'x': 45, 'y': 55},
        {'refdes': 'U2', 'desc': 'LDO 3.3V', 'cat': 'IC', 'net': 'SYS_3V3', 'critical': True, 'x': 50, 'y': 40},
        {'refdes': 'C2', 'desc': '10uF Cap', 'cat': 'Capacitor', 'net': 'SYS_3V3', 'critical': False, 'x': 55, 'y': 45},
        
        # DIGITAL
        {'refdes': 'U1', 'desc': 'STM32G4 MCU', 'cat': 'IC', 'net': 'SYS_3V3', 'critical': True, 'x': 70, 'y': 50},
        {'refdes': 'U5', 'desc': 'SPI Flash 16MB', 'cat': 'IC', 'net': 'SPI_BUS', 'critical': True, 'x': 85, 'y': 60},
        {'refdes': 'Y1', 'desc': '16MHz Crystal', 'cat': 'Oscillator', 'net': 'SYS_3V3', 'critical': True, 'x': 65, 'y': 60},
        
        # COMMS
        {'refdes': 'U4', 'desc': 'ESP32 WiFi', 'cat': 'IC', 'net': 'SYS_3V3', 'critical': True, 'x': 80, 'y': 20},
        {'refdes': 'A1', 'desc': 'PCB Antenna', 'cat': 'Antenna', 'net': 'RF_OUT', 'critical': True, 'x': 90, 'y': 10},
        
        # SENSORS (ANALOG/I2C)
        {'refdes': 'U6', 'desc': 'BME280 Env', 'cat': 'IC', 'net': 'I2C_BUS', 'critical': False, 'x': 30, 'y': 80},
        {'refdes': 'U7', 'desc': 'MPU6050 IMU', 'cat': 'IC', 'net': 'I2C_BUS', 'critical': False, 'x': 50, 'y': 80},
        {'refdes': 'R1', 'desc': '10k Pullup', 'cat': 'Resistor', 'net': 'I2C_BUS', 'critical': False, 'x': 40, 'y': 75},
        {'refdes': 'R2', 'desc': '10k Pullup', 'cat': 'Resistor', 'net': 'I2C_BUS', 'critical': False, 'x': 40, 'y': 78},
        {'refdes': 'R12', 'desc': 'Thermistor', 'cat': 'Resistor', 'net': 'ADC_1', 'critical': False, 'x': 20, 'y': 80},
        {'refdes': 'R13', 'desc': 'Div Resistor', 'cat': 'Resistor', 'net': 'ADC_1', 'critical': False, 'x': 25, 'y': 80},
        
        # OUTPUTS
        {'refdes': 'Q1', 'desc': 'N-Ch MOSFET', 'cat': 'Transistor', 'net': 'PWM_OUT', 'critical': True, 'x': 80, 'y': 80},
        {'refdes': 'J2', 'desc': 'Motor Conn', 'cat': 'Connector', 'net': 'PWM_OUT', 'critical': True, 'x': 90, 'y': 90}
    ]
    pd.DataFrame(components).to_csv('data/components.csv', index=False)
    
    # 2. Net Connections (Pin Level)
    nets = [
        {'refdes': 'J1', 'pin': 'VBUS', 'net_name': 'VBUS_5V', 'pin_role': 'SOURCE'},
        {'refdes': 'F1', 'pin': '1', 'net_name': 'VBUS_5V', 'pin_role': 'PASSIVE'},
        {'refdes': 'F1', 'pin': '2', 'net_name': 'FUSED_5V', 'pin_role': 'PASSIVE'},
        {'refdes': 'U3', 'pin': 'VIN', 'net_name': 'FUSED_5V', 'pin_role': 'POWER_IN'},
        {'refdes': 'U3', 'pin': 'SW', 'net_name': 'SW_NODE', 'pin_role': 'POWER_OUT'},
        {'refdes': 'L1', 'pin': '1', 'net_name': 'SW_NODE', 'pin_role': 'PASSIVE'},
        {'refdes': 'L1', 'pin': '2', 'net_name': 'SYS_5V', 'pin_role': 'PASSIVE'},
        {'refdes': 'C1', 'pin': '1', 'net_name': 'SYS_5V', 'pin_role': 'PASSIVE'},
        {'refdes': 'U2', 'pin': 'VIN', 'net_name': 'SYS_5V', 'pin_role': 'POWER_IN'},
        {'refdes': 'U2', 'pin': 'VOUT', 'net_name': 'SYS_3V3', 'pin_role': 'POWER_OUT'},
        {'refdes': 'C2', 'pin': '1', 'net_name': 'SYS_3V3', 'pin_role': 'PASSIVE'},
        {'refdes': 'U1', 'pin': 'VDD', 'net_name': 'SYS_3V3', 'pin_role': 'POWER_IN'},
        {'refdes': 'U4', 'pin': 'VDD', 'net_name': 'SYS_3V3', 'pin_role': 'POWER_IN'},
        {'refdes': 'U5', 'pin': 'VCC', 'net_name': 'SYS_3V3', 'pin_role': 'POWER_IN'},
        {'refdes': 'U6', 'pin': 'VCC', 'net_name': 'SYS_3V3', 'pin_role': 'POWER_IN'},
        {'refdes': 'U7', 'pin': 'VCC', 'net_name': 'SYS_3V3', 'pin_role': 'POWER_IN'},
        
        {'refdes': 'U1', 'pin': 'SPI_MOSI', 'net_name': 'SPI_BUS', 'pin_role': 'SIGNAL_OUT'},
        {'refdes': 'U5', 'pin': 'DI', 'net_name': 'SPI_BUS', 'pin_role': 'SIGNAL_IN'},
        
        {'refdes': 'U1', 'pin': 'I2C_SDA', 'net_name': 'I2C_BUS', 'pin_role': 'BIDIR'},
        {'refdes': 'U6', 'pin': 'SDA', 'net_name': 'I2C_BUS', 'pin_role': 'BIDIR'},
        {'refdes': 'U7', 'pin': 'SDA', 'net_name': 'I2C_BUS', 'pin_role': 'BIDIR'},
        {'refdes': 'R1', 'pin': '1', 'net_name': 'I2C_BUS', 'pin_role': 'PASSIVE'},
        
        {'refdes': 'U1', 'pin': 'ADC_IN', 'net_name': 'ADC_1', 'pin_role': 'SIGNAL_IN'},
        {'refdes': 'R12', 'pin': '2', 'net_name': 'ADC_1', 'pin_role': 'PASSIVE'},
        
        {'refdes': 'U1', 'pin': 'PWM', 'net_name': 'PWM_CTRL', 'pin_role': 'SIGNAL_OUT'},
        {'refdes': 'Q1', 'pin': 'GATE', 'net_name': 'PWM_CTRL', 'pin_role': 'SIGNAL_IN'},
        {'refdes': 'Q1', 'pin': 'DRAIN', 'net_name': 'PWM_OUT', 'pin_role': 'POWER_OUT'},
        {'refdes': 'J2', 'pin': '1', 'net_name': 'PWM_OUT', 'pin_role': 'POWER_IN'}
    ]
    pd.DataFrame(nets).to_csv('data/net_connections.csv', index=False)
    
    # 3. Test Net Map
    tests = [
        {'test_step': 'TEST_VBUS', 'net_name': 'VBUS_5V', 'domain': 'POWER', 'level': 0},
        {'test_step': 'TEST_FUSE', 'net_name': 'FUSED_5V', 'domain': 'POWER', 'level': 1},
        {'test_step': 'TEST_5V_RAIL', 'net_name': 'SYS_5V', 'domain': 'POWER', 'level': 2},
        {'test_step': 'TEST_3V3_RAIL', 'net_name': 'SYS_3V3', 'domain': 'POWER', 'level': 3},
        {'test_step': 'TEST_MCU_BOOT', 'net_name': 'SYS_3V3', 'domain': 'DIGITAL', 'level': 4},
        {'test_step': 'TEST_SPI_FLASH', 'net_name': 'SPI_BUS', 'domain': 'DIGITAL', 'level': 5},
        {'test_step': 'TEST_WIFI_ENUM', 'net_name': 'SYS_3V3', 'domain': 'COMMS', 'level': 4},
        {'test_step': 'TEST_RF_POWER', 'net_name': 'RF_OUT', 'domain': 'COMMS', 'level': 5},
        {'test_step': 'TEST_I2C_BUS', 'net_name': 'I2C_BUS', 'domain': 'DIGITAL', 'level': 5},
        {'test_step': 'TEST_THERMISTOR', 'net_name': 'ADC_1', 'domain': 'ANALOG', 'level': 5},
        {'test_step': 'TEST_MOTOR_PWM', 'net_name': 'PWM_OUT', 'domain': 'ANALOG', 'level': 5}
    ]
    pd.DataFrame(tests).to_csv('data/test_net_map.csv', index=False)
    
    # Fault Scenarios (15 realistic failures) — module-level SCENARIOS.
    scenarios = SCENARIOS
    
    # Generate Test Logs and Ground Truth
    test_logs = []
    ground_truth = []
    
    # Normal expected values for tests — module-level EXPECTED.
    expected = EXPECTED
    
    # 500 total instances (300 dev, 100 val, 100 blind test)
    for i in range(500):
        board_id = f"BRD_{i:04d}"
        scenario = random.choice(scenarios)
        
        # Determine dataset split
        if i < 300: split = 'train'
        elif i < 400: split = 'val'
        else: split = 'blind'
        
        ground_truth.append({
            'board_id': board_id,
            'root_cause': scenario['root'],
            'scenario': scenario['name'],
            'split': split
        })
        
        for step, (ex_min, ex_max, unit) in expected.items():
            if step in scenario['tests']:
                # Failing test
                fail_min, fail_max, err_code = scenario['tests'][step]
                meas = random.uniform(fail_min, fail_max)
                status = 'FAIL'
            else:
                # Passing test
                meas = random.uniform(ex_min, ex_max)
                status = 'PASS'
                err_code = ''
                
            test_logs.append({
                'board_id': board_id,
                'test_step': step,
                'measured_value': meas,
                'expected_min': ex_min,
                'expected_max': ex_max,
                'unit': unit,
                'pass_fail': status,
                'error_code': err_code
            })
            
    df_logs = pd.DataFrame(test_logs)
    df_logs.to_csv('data/test_logs.csv', index=False)
    
    df_gt = pd.DataFrame(ground_truth)
    df_gt[df_gt['split'] == 'train'].to_csv('validation/ground_truth_train.csv', index=False)
    df_gt[df_gt['split'] == 'val'].to_csv('validation/ground_truth_val.csv', index=False)
    df_gt[df_gt['split'] == 'blind'].to_csv('validation/ground_truth_blind.csv', index=False)
    
    # 5. Repair History (150 cases for Semantic Memory)
    history = []
    symptom_templates = {
        'U3': ["Board dead, 5V rail measured {v}V. Replaced U3.", "No power to system. SYS_5V failing. U3 buck converter found shorted.", "Complete power cascade failure. U3 damaged."],
        'L1': ["5V rail low voltage. Found L1 cracked.", "Inductor L1 open circuit. Replaced.", "SYS_5V unstable. L1 solder joint failed."],
        'F1': ["Fuse blown. VBUS present but no FUSED_5V.", "F1 PTC fuse tripped permanently. Replaced.", "No power past fuse F1."],
        'U2': ["3.3V rail at {v}V. Replaced U2 LDO.", "MCU not booting. SYS_3V3 down. U2 overheated.", "U2 regulator failed, pulling down 3.3V bus."],
        'U1': ["MCU boot failure. VDD ok but no code execution. Replaced STM32.", "Digital domain failure. U1 dead.", "U1 MCU unresponsive. Re-flashed, failed. Replaced chip."],
        'U5': ["SPI flash read error. Resoldered U5.", "SPI bus failing. U5 chip select pin open.", "Replaced U5 16MB flash."],
        'U4': ["WiFi enum failed. ESP32 dead.", "No RF power. U4 module replaced.", "Comms domain failure. U4 defective."],
        'A1': ["Low RF power output. Antenna disconnected.", "A1 trace broken.", "Re-soldered A1 antenna connection."],
        'U6': ["I2C bus locked. U6 sensor shorting SDA.", "Removed U6, I2C bus recovered. Replaced BME280.", "U6 internal short."],
        'R1': ["I2C pullup R1 missing.", "R1 open. I2C bus floating.", "Replaced R1 10k resistor."],
        'R12': ["Thermistor reading open.", "R12 damaged.", "ADC reading wrong. Replaced R12."],
        'Q1': ["Motor always on. Q1 shorted drain to source.", "Q1 MOSFET blown.", "Replaced Q1."],
        'C1': ["5V rail ripple high under load. C1 missing.", "C1 bulk cap tombstoned.", "Replaced C1 22uF."],
        'C2': ["3.3V rail shorted to ground. C2 ceramic cap cracked.", "C2 shorted. Removed and replaced.", "Dead board. Found C2 shorting SYS_3V3."],
        'J1': ["USB connector pins shorted inside.", "J1 damaged by user. Replaced.", "VBUS short to ground at J1 connector."]
    }
    
    # Generate 150 historical cases (10 of each scenario type)
    for root_cause, templates in symptom_templates.items():
        for i in range(10):
            template = random.choice(templates)
            volt = round(random.uniform(0.1, 1.5), 2)
            desc = template.format(v=volt)
            
            # Find the corresponding scenario to get typical failed steps
            rel_scen = next((s for s in scenarios if s['root'] == root_cause), scenarios[0])
            failed_steps = list(rel_scen['tests'].keys())
            
            history.append({
                'repair_id': f"REP-{uuid.uuid5(uuid.NAMESPACE_DNS, f'circuitmind-{RANDOM_SEED}-{root_cause}-{i}').hex[:6].upper()}",
                'symptom_text': desc,
                'failed_steps': '|'.join(failed_steps),
                'root_cause_component': root_cause,
                'fix_action': 'REPLACED' if 'Replace' in desc else 'RE-SOLDERED'
            })
            
    pd.DataFrame(history).to_csv('data/repair_history.csv', index=False)
    print("Data Generation Complete! ✅")

if __name__ == "__main__":
    generate_all_data()
