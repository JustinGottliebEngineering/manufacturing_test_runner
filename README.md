# Manufacturing Test Runner

A Flask-based portfolio project demonstrating how manufacturing test and device-programming procedures can be managed through a standardized technician interface.

The application will execute simulated test procedures, stream live console output, record pass/fail results, preserve test setup information for reruns, and demonstrate safe resource cleanup.

All products, equipment, test procedures, data, and hardware responses in this repository are fictional and independently created for demonstration purposes.

## Project Purpose

Manufacturing test stations often require technicians to work with multiple utilities, scripts, instruments, programming tools, firmware files, and product-specific procedures.

This can create several risks:

* Incorrect test procedure selection
* Incorrect firmware selection
* Repeated manual data entry
* Inconsistent technician workflows
* Incomplete result records
* Stale serial-port or instrument connections
* Limited visibility during long-running procedures
* Difficulty rerunning or recovering from interrupted tests

This project demonstrates a software architecture for consolidating those workflows into one controlled application.

## Planned Capabilities

### Test Setup

* Select a fictional product
* Enter a work-order number
* Enter a serial number
* Select an available test procedure
* Validate required setup information
* Preserve entered data during reruns

### Test Execution

* Launch Python test procedures
* Stream live output to the browser
* Display test progress
* Display technician instructions
* Record start and completion times
* Return pass, fail, aborted, or error status

### Simulated Hardware

* Simulated serial instrument
* Simulated programmable power supply
* Simulated frequency counter
* Simulated device programmer
* Configurable delays and responses
* Controlled communication failures
* Retry and timeout behavior

### Rerun and Recovery

* Rerun the most recent procedure
* Preserve work-order and serial-number data
* Abort an active procedure
* Release simulated hardware resources
* Prevent stale test sessions
* Record each execution attempt separately

### Result Tracking

* Store completed test runs
* Record procedure name
* Record product and serial number
* Record start and completion timestamps
* Record pass/fail status
* Record console output
* Display recent test history

### Engineering Controls

* Separate product configuration from execution logic
* Use a common test-procedure interface
* Validate procedure inputs
* Handle subprocess errors
* Handle timeouts
* Ensure cleanup after success, failure, or abort
* Prevent simultaneous use of the same simulated station

## Proposed Technology

* Python
* Flask
* SQLite
* HTML
* CSS
* JavaScript
* Server-sent events
* Python subprocess management
* Automated testing with pytest
* GitHub Actions continuous integration

## Proposed Repository Structure

```text
manufacturing-test-runner/
├── .github/
│   └── workflows/
│       └── python-tests.yml
├── README.md
├── requirements.txt
├── run.py
├── instance/
├── src/
│   └── manufacturing_test_runner/
│       ├── __init__.py
│       ├── database.py
│       ├── models.py
│       ├── routes.py
│       ├── runner.py
│       ├── services/
│       │   ├── result_service.py
│       │   └── test_service.py
│       ├── simulators/
│       │   ├── base.py
│       │   ├── frequency_counter.py
│       │   ├── power_supply.py
│       │   └── serial_device.py
│       ├── procedures/
│       │   ├── base.py
│       │   ├── sensor_calibration.py
│       │   └── controller_functional_test.py
│       ├── static/
│       │   ├── css/
│       │   │   └── app.css
│       │   └── js/
│       │       └── test_runner.js
│       └── templates/
│           ├── base.html
│           ├── setup.html
│           ├── result.html
│           └── history.html
└── tests/
    ├── test_procedures.py
    ├── test_routes.py
    ├── test_runner.py
    └── test_simulators.py
```

## Example Fictional Products

The demonstration may include products such as:

* `SENSOR-MODULE-100`
* `CONTROL-BOARD-200`
* `RF-DEMO-300`

These identifiers are fictional and are not based on employer or customer products.

## Example Test Procedures

### Sensor Calibration

A simulated calibration procedure may:

1. Detect the simulated power supply
2. Apply a configured voltage
3. Read simulated sensor output
4. Compare results against limits
5. Record calibration values
6. Return pass or fail
7. Release the simulated instrument

### Controller Functional Test

A simulated functional test may:

1. Open a serial connection
2. Request device identification
3. Execute a series of commands
4. Validate responses
5. Simulate a timeout or retry
6. Record results
7. Close the serial connection

## Confidentiality and Data Policy

This repository will not contain:

* Employer-owned source code
* Production test scripts
* Customer information
* Actual product numbers
* Firmware
* Proprietary communication protocols
* Internal network paths
* Credentials
* Access tokens
* Manufacturing specifications
* Equipment configuration files
* Production databases

The project is being developed independently as a clean-room portfolio demonstration.

## Professional Context

This project reflects practical experience with:

* Manufacturing test automation
* Flask production interfaces
* Python subprocess execution
* Live console-output streaming
* Embedded-device programming workflows
* Serial and instrument communication
* Long-running test procedures
* Technician instructions
* Abort and rerun handling
* Hardware-resource cleanup
* Test-result traceability
* Production deployment and troubleshooting

## Project Status

Initial architecture and project structure are being developed.
