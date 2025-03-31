# QSHA - Quantum-Salted Hash Algorithm

## True Quantum Randomness in Cryptographic Hashing

QSHA leverages **true quantum randomness** from IBM's quantum computers to create a novel approach to cryptographic hashing. While conventional SHA-256 is deterministic (same input always produces the same output), QSHA introduces quantum uncertainty into the hashing process:

1. **Quantum Salt Generation**: For each hash operation, we generate 256 random bits using real quantum measurements from IBM Quantum hardware
2. **Non-Deterministic Hashing**: The same input will produce different outputs on each execution due to fresh quantum randomness
3. **Hardware-Based Entropy**: Unlike pseudo-random number generators, our entropy comes from fundamental quantum mechanical processes

## How Quantum Randomness Improves Hashing

Traditional SHA algorithms use fixed initialization vectors and deterministic operations. QSHA enhances this by:

- **XORing quantum random bits** with the initial hash values
- Ensuring unpredictability even for identical inputs
- Creating hash digests influenced by true quantum mechanical uncertainty
- Providing a novel experimental approach to non-deterministic hashing

## Overview

QSHA is an experimental command-line tool that generates a fixed-size hash digest (currently 256-bit, similar to SHA-256) for an input message.

Its unique characteristic is the incorporation of randomness generated **exclusively from a real IBM Quantum computer backend**. This "quantum salt" is generated fresh for *each* hash operation and integrated into the hashing process (specifically, by XORing with the initial hash values). Access to IBM Quantum (via API key/credentials) is **required** for this tool to function.

**Key Feature:** Due to the fresh quantum salt used each time, hashing the **same input message multiple times will produce different output digests.**

**Disclaimer:** QSHA is an **experimental tool** exploring the combination of real quantum randomness and classical hashing concepts. It is **NOT a standard cryptographic hash function** and **should NOT be used for security-critical applications** that rely on deterministic hashing (e.g., password storage, data integrity checks where the same input must always yield the same hash). Its collision resistance and other cryptographic properties are different from standard SHA algorithms and have not been rigorously analyzed. **Using this tool will consume IBM Quantum resources/credits.**

## Features

*   **Quantum Random Bit Generator (QRBG):** Generates random bits using Qiskit, connecting **exclusively** to a real IBM Quantum backend.
*   **Quantum-Salted Hash (QSHA-256):** Implements a SHA-256-like algorithm where the initial state is perturbed by a fresh 256-bit quantum salt (obtained from the QRBG) before processing the message.
*   **Command-Line Interface (CLI):** Simple interface (`qsha_cli.py`) to hash messages provided as arguments or via standard input. Requires IBM Quantum connection to succeed.

## Requirements

*   Python 3.x
*   Qiskit packages:
    *   `qiskit`
*   `qiskit-ibm-runtime` (required for IBM Quantum access)

## Installation & Setup

1.  **Clone or Download:** Get the project files (`qsha_cli.py`, `qsha.py`, `qrbg.py`).
    ```bash
    # Example using git:
    # git clone <repository_url>
    # cd <repository_directory>
    ```
2.  **Install Dependencies:**
    ```bash
    pip install qiskit qiskit-aer qiskit-ibm-runtime
    ```bash
    pip install qiskit qiskit-ibm-runtime
    ```
    *(Consider using a Python virtual environment. `qiskit-aer` is no longer strictly required by this tool but might be useful for other Qiskit tasks.)*

3.  **IBM Quantum Setup (Required):**
    This tool **requires** access to a real IBM Quantum backend. You **must** provide your API credentials. The tool prioritizes credentials in this order:
    *   **Saved Account:** Credentials saved using Qiskit's utility. Run this once in a Python environment:
        ```python
        from qiskit_ibm_runtime import QiskitRuntimeService
        # Follow prompts or provide token/instance directly:
        QiskitRuntimeService.save_account(channel='ibm_quantum', token='YOUR_IBM_QUANTUM_API_TOKEN', instance='YOUR_IBM_QUANTUM_INSTANCE')
        # Example instance: 'ibm-q/open/main'
        ```
    *   **Environment Variables:** Set these in your shell before running the tool:
        ```bash
        export IBM_QUANTUM_TOKEN="YOUR_IBM_QUANTUM_API_TOKEN"
        export IBM_QUANTUM_INSTANCE="YOUR_IBM_QUANTUM_INSTANCE"
        ```

    **If you do not perform this setup, or if the credentials are invalid or no suitable backend can be accessed, the tool will fail with an error.**

## Usage

The main script is `qsha_cli.py`.

```bash
# Basic usage (requires IBM Quantum setup)
python3 qsha_cli.py "Your message here"

# Hash message from standard input
echo "Piped message" | python3 qsha_cli.py

# Verbose mode (shows INFO logs from QRBG/QSHA steps)
python3 qsha_cli.py "Debug message" --verbose

# Show help message
python3 qsha_cli.py --help
```

**Expected Output:**

The script prints the 64-character hexadecimal QSHA-256 digest to standard output and the source of randomness (the IBM backend name) to standard error. If connection or execution fails, it prints an error message to standard error.

```
# Example successful output
$ python3 qsha_cli.py "Test"
Computing QSHA-256 hash using IBM Quantum...
a1b2c3d4e5f6... (some 64-char hex string)
Randomness Source: ibm_brisbane
```

# Example error output (if credentials fail)
$ python3 qsha_cli.py "Test"
Computing QSHA-256 hash using IBM Quantum...

Error: An exception occurred during QSHA processing.
Ensure IBM Quantum credentials are correctly configured (see README.md).
Details: Failed to initialize IBM Quantum Service or find suitable backend: ('Credentials missing or invalid', ...)
```

Remember, running the same command again will produce a *different* hash.

## How It Works (Briefly)

1.  The `qsha_cli.py` script parses arguments and gets the input message.
2.  It calls the `qsha256` function in `qsha.py`.
3.  `qsha256` requests 256 random bits from the `QuantumRandomBitGenerator` (`qrbg.py`).
4.  `qrbg.py` connects to IBM Quantum using your configured credentials and selects a suitable backend. If this fails, an error is raised.
5.  `qrbg.py` generates the 256 bits by running a 1-qubit Hadamard+Measure circuit multiple times (shots) on the selected IBM Quantum backend.
6.  The 256 random bits (the "quantum salt") are returned to `qsha256`.
7.  `qsha256` converts the salt bits into eight 32-bit integers.
8.  These salt integers are XORed with the standard initial hash values (H0-H7) of SHA-256.
9.  The rest of the SHA-256 algorithm (padding, message scheduling, compression rounds) proceeds using these *salted* initial values.
10. The final 256-bit hash digest is formatted as hexadecimal and returned along with the source name.

## Limitations

*   **Non-Deterministic:** As emphasized, this tool produces different hashes for the same input on different runs. Do not use it where deterministic output is required.
*   **Security:** Not a replacement for standard cryptographic hashes like SHA-256. Its security properties are unknown and likely weaker in standard contexts.
*   **Performance:** Using a real IBM Quantum backend can be **very slow** due to job queuing times. Expect delays.
*   **Cost:** Executing jobs on IBM Quantum backends consumes resources which may be limited depending on your plan.
*   **Randomness Quality:** Randomness from real backends is subject to device noise, calibration, and potential biases. It's not guaranteed to be perfectly uniform or statistically ideal without further post-processing (which this tool does not do).
*   **Fixed Size:** Currently hardcoded for a 256-bit output and salt.
