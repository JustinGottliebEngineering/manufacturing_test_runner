# Manufacturing Test Runner

A portfolio demonstration of a technician-facing manufacturing test application built with Python, Flask, SQLite, JavaScript, and simulated test equipment.

The application models the architecture of a production test station without requiring proprietary hardware, production data, or vendor software. It executes manufacturing procedures, streams live test output to the browser, records measurements, handles failures and abort requests, and stores completed test records in a searchable SQLite history database.

## Screenshots

### Test Setup

![Test setup](docs/screenshots/test-setup.png)

### Live Procedure Execution

![Live passing test](docs/screenshots/live-passing-test.png)

### Failed Test Result

![Failed test](docs/screenshots/failed-test.png)

### Persistent Test History

![Test history](docs/screenshots/test-history.png)

### Stored Result Detail

![History detail](docs/screenshots/history-detail.png)

## Application Overview

Manufacturing Test Runner demonstrates how automated test software can convert a complex engineering process into a controlled and repeatable technician workflow.

A technician enters a work order and serial number, selects a test procedure and demonstration scenario, and starts the test. The application then:

1. Creates a uniquely identified test run.
2. Executes the selected procedure in a worker thread.
3. Streams procedure messages to the browser using server-sent events.
4. Coordinates simulated instruments and serial devices.
5. Evaluates measurements against engineering limits.
6. Reports PASS, FAIL, ERROR, or ABORTED status.
7. Performs instrument cleanup even when execution fails.
8. Stores the completed result in SQLite.
9. Makes the record available through searchable test history.

## Key Features

* Technician-oriented Flask web interface
* Live procedure output using server-sent events
* Background test execution
* Responsive procedure abort handling
* Rerun support with preserved production identifiers
* Station concurrency protection
* Configurable PASS, FAIL, retry, and timeout demonstrations
* Simulated programmable power supply
* Simulated frequency counter
* Simulated serial-controlled device
* Measurement capture and engineering-limit evaluation
* Structured procedure results
* Guaranteed resource cleanup
* Persistent SQLite test history
* History filtering by work order, serial number, procedure, and status
* Detailed saved-result views
* Automated unit, integration, route, persistence, and concurrency tests

## Demonstration Procedures

### Sensor Module Calibration

The sensor calibration procedure coordinates a simulated programmable power supply and frequency counter.

The procedure:

* Connects to both instruments
* Configures supply voltage and current limit
* Enables power to the simulated unit under test
* Allows the unit to stabilize
* Measures supply voltage and current
* Enables the frequency-counter input
* Measures oscillator frequency
* Calculates frequency error in hertz and parts per million
* Compares measurements against calibration limits
* Reports the final test status
* Disables and disconnects instruments during cleanup

Available scenarios:

| Scenario                   | Expected result                                    |
| -------------------------- | -------------------------------------------------- |
| Standard passing procedure | PASS                                               |
| Deliberate test failure    | FAIL due to oscillator frequency outside tolerance |

### Controller Functional Test

The controller functional test communicates with a simulated serial-controlled device.

The procedure:

* Opens the serial connection
* Requests device identification
* Verifies the expected controller model
* Requests controller status
* Executes the internal self-test
* Supports communication retries
* Simulates timeout behavior
* Evaluates returned responses
* Reports the final test status
* Disconnects the serial device during cleanup

Available scenarios:

| Scenario                      | Expected result                |
| ----------------------------- | ------------------------------ |
| Standard passing procedure    | PASS                           |
| Deliberate test failure       | FAIL due to self-test mismatch |
| Transient communication retry | PASS after retry               |
| Communication timeout         | ERROR                          |

## Live Test Execution

Tests execute outside the HTTP request thread.

The `LiveRunManager` creates a background worker for each run and publishes structured events as the procedure progresses. The result page connects to the event endpoint using the browser `EventSource` API.

Event types include:

* `run_started`
* `procedure_message`
* `abort_requested`
* `result`
* `execution_error`
* `complete`

This design allows the interface to remain responsive while a long-running manufacturing procedure is active.

## Abort and Cleanup Behavior

An active procedure can receive an abort request from the browser.

Procedure delays are divided into short intervals so abort requests can be detected promptly. When an abort occurs, the procedure returns an `ABORTED` result and still executes its cleanup logic.

Cleanup behavior is also applied after:

* Passing procedures
* Failed limit evaluations
* Communication errors
* Instrument configuration errors
* Unexpected exceptions

This models an important manufacturing-test requirement: equipment and communication resources must not remain active after an interrupted or unsuccessful test.

## Persistent Test History

Completed test results are stored in SQLite.

Each record includes:

* Run ID
* Work order
* Serial number
* Procedure ID
* Procedure name
* Demonstration scenario
* Final status
* PASS indicator
* Measurements
* Error messages
* UTC completion timestamp

The history page supports filtering by:

* Work order
* Serial number
* Procedure
* Final status

Measurements and errors are serialized as JSON so procedure-specific data can be stored without requiring a separate database schema for each procedure.

## Architecture

```text
Browser
   |
   | HTTP forms, fetch requests, and EventSource
   v
Flask Routes
   |
   +--> LiveRunManager
   |       |
   |       +--> Background worker thread
   |       |
   |       +--> Server-sent event queue
   |
   +--> ProcedureRunner
   |       |
   |       +--> Station execution lock
   |       +--> Active procedure tracking
   |       +--> Abort forwarding
   |
   +--> Manufacturing Procedures
   |       |
   |       +--> SensorCalibrationProcedure
   |       +--> ControllerFunctionalTestProcedure
   |
   +--> Simulated Equipment
   |       |
   |       +--> SimulatedPowerSupply
   |       +--> SimulatedFrequencyCounter
   |       +--> SimulatedSerialDevice
   |
   +--> TestHistoryStore
           |
           +--> SQLite
```

## Project Structure

```text
manufacturing_test_runner/
├── run.py
├── README.md
├── pyproject.toml
├── src/
│   └── manufacturing_test_runner/
│       ├── __init__.py
│       ├── history_store.py
│       ├── live_runs.py
│       ├── routes.py
│       ├── runner.py
│       ├── procedures/
│       │   ├── base.py
│       │   ├── controller_functional_test.py
│       │   └── sensor_calibration.py
│       ├── simulators/
│       │   ├── base.py
│       │   ├── frequency_counter.py
│       │   ├── power_supply.py
│       │   └── serial_device.py
│       ├── static/
│       │   └── css/
│       │       └── app.css
│       └── templates/
│           ├── base.html
│           ├── history.html
│           ├── history_detail.html
│           ├── result.html
│           └── setup.html
└── tests/
    ├── test_history_store.py
    ├── test_procedures.py
    ├── test_routes.py
    ├── test_runner.py
    └── test_simulators.py
```

## Technology Stack

| Technology         | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| Python             | Application, procedure, and simulator logic        |
| Flask              | Web application and HTTP routing                   |
| SQLite             | Persistent test-result storage                     |
| HTML and CSS       | Technician-facing interface                        |
| JavaScript         | Live result updates and abort requests             |
| Server-Sent Events | One-way live procedure streaming                   |
| Threading          | Background procedure execution and station locking |
| Pytest             | Automated testing                                  |
| GitHub Actions     | Continuous integration                             |

## Local Setup

### 1. Clone the repository

```powershell
git clone https://github.com/JustinGottliebEngineering/manufacturing_test_runner.git
cd manufacturing_test_runner
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install the project

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 5. Run the automated tests

```powershell
python -m pytest -v
```

The current test suite contains 70 passing tests covering simulator behavior, procedure execution, concurrency protection, live routes, persistent history, filtering, and error handling.

### 6. Start the application

```powershell
python .\run.py
```

Open the application at:

```text
http://127.0.0.1:5000
```

## Suggested Demonstration

For a complete application demonstration:

1. Run Sensor Module Calibration in passing mode.
2. Review the live console and recorded measurements.
3. Rerun the procedure.
4. Run Sensor Module Calibration in deliberate-failure mode.
5. Run Controller Functional Test in retry mode.
6. Run Controller Functional Test in timeout mode.
7. Start a timed procedure and use the abort button.
8. Open Test History.
9. Filter results by procedure and final status.
10. Open an individual stored result.

## Automated Testing

The test suite covers:

* Simulator connection enforcement
* Power-supply configuration and measurement
* Frequency-counter measurement and forced readings
* Serial command normalization
* Unsupported serial commands
* Transient communication failures
* Retry exhaustion
* Communication timeouts
* Procedure PASS and FAIL decisions
* Procedure message callbacks
* Instrument cleanup
* Procedure setup errors
* Runner procedure selection
* Station concurrency protection
* Abort behavior
* Rerun behavior
* Flask form validation
* Live result pages
* Server-sent event output
* Persistent history storage
* Duplicate run protection
* History filtering
* Stored-result retrieval
* Unknown run and history-record handling

Run the suite with:

```powershell
python -m pytest -v
```

## Continuous Integration

The repository is intended to run the automated test suite through GitHub Actions for every push and pull request.

This provides immediate verification that changes do not break:

* Procedure logic
* Equipment simulators
* Flask routes
* Live execution
* Persistence
* Test-history filtering

## Engineering Concepts Demonstrated

This project demonstrates several patterns used in real manufacturing test systems:

* Separation of web, orchestration, procedure, and equipment layers
* Abstract equipment interfaces
* Deterministic hardware simulation
* Procedure-specific measurement limits
* Resource ownership and cleanup
* Background execution
* Live technician feedback
* Cooperative cancellation
* Station-level concurrency control
* Structured result records
* Persistent traceability
* Failure injection
* Automated regression testing

## Portfolio Context

This is a standalone portfolio project built with fictional identifiers and simulated equipment.

It does not contain:

* Employer source code
* Proprietary test procedures
* Production credentials
* Customer information
* Product firmware
* Confidential manufacturing data
* Vendor-restricted documentation

The project is intended to demonstrate software architecture, manufacturing-test automation, equipment coordination, test traceability, and technician-interface design using independently written code.

## Future Enhancements

Potential future additions include:

* CSV result export
* PDF test reports
* User authentication and technician identification
* Role-based access
* Procedure revision tracking
* Configurable limits stored in the database
* Barcode-scanner input
* Equipment calibration status
* REST API endpoints
* WebSocket-based bidirectional communication
* Production deployment configuration
* Additional simulated instruments and test procedures
