# Product Requirements Document: QSHA - Quantum-Salted Hash Tool

**Version:** 1.0
**Date:** 2025-03-30

## 1. Introduction

QSHA (Quantum-Salted Hash Algorithm) is a command-line utility designed to generate a fixed-size hash digest for an input message. Unlike standard cryptographic hash functions (like SHA-256), QSHA incorporates randomness generated **exclusively from a real IBM Quantum computer backend** into its process. This "quantum salt" ensures that hashing the same input message multiple times will produce *different* output digests. QSHA is intended as an exploration of combining real quantum phenomena with classical hashing concepts, not as a replacement for standard, deterministic cryptographic hashes. **Access to IBM Quantum is required.**

## 2. Goals

*   **G1:** Develop a tool that produces a non-deterministic, SHA-like hash digest using **real** quantum randomness as a salt.
*   **G2:** Require configured IBM Quantum credentials for operation.
*   **G3:** Offer a simple command-line interface for ease of use.
*   **G4:** Structure the code modularly (QRBG, QSHA logic, CLI).
*   **G5:** Clearly communicate the non-deterministic nature and intended use cases (or lack thereof for standard crypto applications).

## 3. User Stories

*   **US1:** As a user interested in quantum computing applications, I want to hash a message using QSHA so that I can see a hash influenced by quantum randomness.
*   **US2:** As a developer, I want to specify the desired output hash length (e.g., 256 bits) so that I can control the size of the digest.
*   **US3:** (Removed - Simulator is not supported)
*   **US4:** As a user, I want to provide the input message directly via the command line or pipe it from another command so that the tool integrates easily into scripts.
*   **US5:** As a user, I want to know which specific IBM Quantum backend generated the randomness so that I understand the source of the non-determinism.

## 4. Functional Requirements

Based on the features defined in `roadmap.md`:

### FR1: Quantum Random Bit Generator (QRBG)

*   **FR1.1:** The system MUST provide a function/class to generate `N` random bits.
*   **FR1.2:** The QRBG MUST attempt to initialize `QiskitRuntimeService` using environment variables (`IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE`) or saved credentials.
*   **FR1.3:** If `QiskitRuntimeService` initialization succeeds, the QRBG MUST select an available, operational, non-simulator backend (e.g., least busy).
*   **FR1.4:** If `QiskitRuntimeService` initialization fails or no suitable backend is found, the QRBG MUST raise an exception. **No simulator fallback.**
*   **FR1.5:** The QRBG MUST construct quantum circuits consisting of a Hadamard gate and a measurement on a single qubit.
*   **FR1.6:** The QRBG MUST execute the 1-qubit circuit for `N` shots (where `N` is the number of bits required), potentially in batches, on the selected IBM Quantum backend.
*   **FR1.7:** The QRBG MUST extract the measurement outcomes ('0' or '1') from the job results and concatenate them to form the final bit string/list.
*   **FR1.8:** The QRBG MUST return the generated bit sequence and the name of the IBM backend used.
*   **FR1.9:** The QRBG MUST handle potential exceptions during job execution gracefully (e.g., job failure) but MUST raise exceptions during initialization/backend selection if IBM Quantum access fails.

### FR2: Quantum-Salted Hash Function (QSHA)

*   **FR2.1:** The system MUST provide a function that accepts an input message (bytes) and a desired output hash length in bits (currently fixed at 256).
*   **FR2.2:** For each call, the QSHA function MUST invoke the QRBG (FR1) to generate a fresh quantum random salt (length 256 bits). This call may raise exceptions if QRBG initialization fails.
*   **FR2.3:** The QSHA function MUST implement a deterministic internal algorithm based on SHA-256 principles (padding, message scheduling, iterative compression function).
    *   **FR2.3.1 (Padding):** The input message MUST be padded to a multiple of the block size (e.g., 512 bits). Padding MUST include the original message length, similar to SHA.
    *   **FR2.3.2 (Initialization Vector - IV):** Fixed initial hash values (constants) MUST be defined, similar to standard SHA algorithms.
    *   **FR2.3.3 (Compression Function):** An internal compression function MUST process message blocks iteratively, updating the internal hash state.
    *   **FR2.3.4 (Salt Integration):** The quantum salt MUST be integrated into the compression function's rounds. This could involve XORing salt bits with intermediate hash values, message schedule words, or round constants at defined points in the process. The exact mechanism needs detailed design.
*   **FR2.4:** The QSHA function MUST produce a final hash digest of the specified length.
*   **FR2.5:** The final hash digest MUST be returned, typically as a hexadecimal string.
*   **FR2.6:** The QSHA function MUST also return the source indicator provided by the QRBG.

### FR3: Command-Line Interface (CLI)

*   **FR3.1:** The system MUST provide an executable Python script (e.g., `qsha.py`).
*   **FR3.2:** The CLI MUST accept the input message:
    *   As a command-line argument (e.g., `python3 qsha_cli.py "my message"`).
    *   Via standard input (e.g., `echo "my message" | python3 qsha_cli.py`).
*   **FR3.3:** The CLI MUST accept an optional argument to specify the desired hash length in bits (`--bits 256`). Default is 256. (Currently only 256 supported).
*   **FR3.4:** (Removed - No simulator flag)
*   **FR3.5:** The CLI MUST parse the arguments, read the input message, and call the QSHA function (FR2), handling potential exceptions during the call (e.g., QRBG init failure).
*   **FR3.6:** The CLI MUST print the resulting hexadecimal hash digest to standard output upon success.
*   **FR3.7:** The CLI MUST print the name of the IBM Quantum backend used to standard error upon success. If an error occurs, it MUST print informative error messages to standard error.

## 5. Non-Functional Requirements

*   **NFR1 (Usability):** The CLI should be simple to use with clear options and output.
*   **NFR2 (Performance):** Execution time will be **highly dependent** on the selected IBM Quantum backend's queue times and execution speed. **Expect significant delays.** The classical hashing part is relatively fast.
*   **NFR3 (Reliability):** The tool MUST handle errors gracefully (invalid input, Qiskit API errors, backend/job execution issues) and provide informative messages. It MUST fail clearly if IBM Quantum access is not possible.
*   **NFR4 (Security):** **Crucially, QSHA is NOT intended for standard cryptographic security applications.** It does not provide deterministic hashing, and its collision resistance properties are unknown and different from standard SHA. API keys MUST be handled securely via environment variables or Qiskit's credential manager, not hardcoded.
*   **NFR4.1 (Cost):** Use of this tool consumes IBM Quantum resources/credits.
*   **NFR5 (Maintainability):** Code should be modular (QRBG, QSHA, CLI separated), well-commented, and potentially include unit tests.

## 6. Design Considerations

*   **DC1 (QSHA Algorithm Details):** The specific method for integrating the quantum salt into the SHA-like structure needs careful design. Options include XORing with intermediate hash states, message words, or round constants. The choice will impact the diffusion of randomness. A simple, clear approach is preferred initially. Using SHA-256 structure as a base seems reasonable.
*   **DC2 (QRBG Backend Selection):** Use the least busy operational, non-simulator backend available via the configured service.
*   **DC3 (QRBG Bit Generation):** Generate N bits using N shots on a single-qubit circuit, potentially batched according to backend limits. Use `memory=True` on simulators if available, otherwise use counts on real hardware. *Correction*: The current implementation uses counts for real hardware. Stick with this for simplicity/cost unless `memory=True` proves feasible.
*   **DC4 (Salt Length):** Use a 256-bit salt, matching the QSHA-256 output size.

## 7. Out of Scope / Non-Goals

*   **NG1:** Achieving cryptographic security properties (collision resistance, pre-image resistance) equivalent to standard SHA algorithms.
*   **NG2:** Providing deterministic hashing (the core feature is non-determinism).
*   **NG3:** Implementing an encryption algorithm.
*   **NG4:** Creating a graphical user interface (GUI).
*   **NG5:** Supporting simulator usage or operation without IBM Quantum credentials.
*   **NG6:** Advanced configuration management beyond API keys/instance.
*   **NG7:** Rigorous analysis of the statistical properties of the generated hashes or the quality of randomness from the specific QPU used.
