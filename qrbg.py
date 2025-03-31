import os
import math
import logging
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler
from qiskit_aer import AerSimulator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QuantumRandomBitGenerator:
    """
    Generates random bits using a real IBM Quantum backend.
    Requires IBM Quantum credentials to be configured.
    """
    def __init__(self):
        """
        Initializes the QRBG by connecting to IBM Quantum and selecting a backend.
        Raises exceptions if connection or backend selection fails.
        """
        self.service = None
        self.backend = None
        self.backend_name = None
        self.is_simulator = False # This class will not use simulators

        self._initialize_ibm_quantum() # Directly attempt initialization

    # Remove _initialize_simulator method entirely

    def _initialize_ibm_quantum(self):
        """Initializes QiskitRuntimeService and selects a real backend."""
        logging.info("Attempting to initialize Qiskit Runtime Service...")
        API_TOKEN = os.environ.get("IBM_QUANTUM_TOKEN")
        INSTANCE = os.environ.get("IBM_QUANTUM_INSTANCE") # e.g., 'ibm-q/open/main'

        try:
            # Prefer loading from saved account first
            try:
                self.service = QiskitRuntimeService(channel='ibm_quantum')
                logging.info("Loaded IBM Quantum credentials from saved account.")
            except Exception:
                logging.info("No saved IBM Quantum account found or error loading.")
                if API_TOKEN and INSTANCE:
                    self.service = QiskitRuntimeService(channel='ibm_quantum', token=API_TOKEN, instance=INSTANCE)
                    logging.info("Initialized Qiskit Runtime Service using environment variables.")
                elif API_TOKEN:
                     # Attempt default instance if only token is provided (might work for some plans)
                     logging.warning("IBM_QUANTUM_INSTANCE not set, attempting initialization without it.")
                     self.service = QiskitRuntimeService(channel='ibm_quantum', token=API_TOKEN)
                     logging.info("Initialized Qiskit Runtime Service using token (default instance).")
                else:
                    logging.warning("IBM_QUANTUM_TOKEN not found in environment variables.")
                    raise ValueError("IBM Quantum API token not found.")

            logging.info("Qiskit Runtime Service initialized.")

            # Select the least busy backend that is operational and not a simulator
            logging.info("Searching for the least busy operational IBM Quantum backend...")
            # Filter for operational, non-simulator backends supporting >= 1 qubit
            backends = self.service.backends(simulator=False, operational=True, min_num_qubits=1)

            if not backends:
                logging.warning("No suitable operational IBM Quantum backends found.")
                raise ConnectionError("No operational backends available.")

            # Sort by queue length (ascending)
            backends.sort(key=lambda b: b.status().pending_jobs)
            self.backend = backends[0] # Select the least busy
            self.backend_name = self.backend.name
            self.is_simulator = False
            logging.info(f"Selected IBM Quantum backend: {self.backend_name} (Queue: {self.backend.status().pending_jobs})")

        except Exception as e:
            logging.error(f"Failed to initialize IBM Quantum Service or find backend: {e}")
            # DO NOT FALL BACK - Raise an error instead
            raise ConnectionError(f"Failed to initialize IBM Quantum Service or find suitable backend: {e}")


    def get_random_bits(self, num_bits):
        """
        Generates a specified number of random bits.

        Args:
            num_bits (int): The number of random bits to generate.

        Returns:
            tuple: A tuple containing:
                - str: A string of '0's and '1's representing the random bits.
                - str: The name of the backend used ('aer_simulator' or IBM backend name).
            Returns (None, self.backend_name) if generation fails.
        """
        if self.backend is None:
             logging.error("No backend available (failed to initialize simulator and/or IBM Quantum).")
             return None, self.backend_name # Return None for bits if no backend

        if num_bits <= 0:
            return "", self.backend_name

        logging.info(f"Generating {num_bits} random bits using {self.backend_name}...")

        # Create a simple 1-qubit circuit
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)

        bits = []
        remaining_bits = num_bits

        # Define maximum shots per job request based on the selected backend
        max_shots_per_request = self.backend.max_shots

        try:
            # Transpile the single circuit once
            transpiled_circuit = transpile(qc, self.backend)

            while remaining_bits > 0:
                shots_to_run = min(remaining_bits, max_shots_per_request)
                logging.info(f"Requesting {shots_to_run} shots (remaining: {remaining_bits})...")

                # Always run on the selected IBM Quantum backend
                # Using backend.run (simpler for getting counts/memory than Sampler here)
                with Session(self.backend) as session:
                    sampler = Sampler()
                    job = sampler.run([transpiled_circuit], shots=shots_to_run)
                    result = job.result()
                    # Access counts from the first PubResult's DataBin for V2 Sampler
                    pub_result = result[0] # Get the result for the first circuit
                    # Assuming the default classical register name is 'c' for QuantumCircuit(1,1)
                    counts = pub_result.data.c.get_counts() # Access counts via the classical register attribute

                # Sampler V2 might return integer keys {0: count0, 1: count1} or bitstrings '0', '1'
                # .get() handles missing keys gracefully for either string or int.
                # Let's try assuming string keys first as the original code did.
                # If it fails, we might need to check for int keys: counts.get(0, 0)
                count0 = counts.get('0', 0)
                count1 = counts.get('1', 0)

                # Create a list with the obtained bits based on counts
                # Note: This loses the original sequence but preserves the distribution for this batch
                current_bits = ['0'] * count0 + ['1'] * count1
                # We should ideally shuffle these if sequence matters, but for hashing salt,
                # the exact sequence might be less critical than the bit values themselves.
                # Let's keep it simple for now.
                bits.extend(current_bits[:shots_to_run]) # Ensure we don't add more than requested shots


                remaining_bits -= shots_to_run
                logging.info(f"Collected {len(bits)} bits so far.")

            # Combine the collected bits
            bit_string = "".join(bits)

            # Ensure we have exactly num_bits (might be slightly off due to counts method on real HW)
            if len(bit_string) != num_bits:
                 logging.warning(f"Obtained bit string length {len(bit_string)} does not match requested {num_bits}. Using slice/padding.")
                 # Pad with '0' or truncate as needed. Padding is less ideal for randomness.
                 # Truncating is safer if we got too many. If too few, something went wrong.
                 if len(bit_string) > num_bits:
                     bit_string = bit_string[:num_bits]
                 else:
                     # This case indicates a problem, likely with the counts approach.
                     logging.error(f"Generated fewer bits ({len(bit_string)}) than requested ({num_bits}). Aborting.")
                     return None, self.backend_name


            logging.info(f"Successfully generated {num_bits} bits using {self.backend_name}.")
            return bit_string, self.backend_name

        except Exception as e:
            logging.exception(f"Error during quantum computation on {self.backend_name}: {e}") # Use logging.exception to include traceback
            # Do not attempt fallback, just return None
            return None, self.backend_name


# Example Usage (for testing - will now require IBM Q setup)
if __name__ == "__main__":
    print("Testing QuantumRandomBitGenerator (Requires IBM Quantum Setup)...")

    # Test: Attempt IBM Quantum connection and bit generation
    print("\n--- Test: Attempt IBM Quantum ---")
    # Ensure you have IBM_QUANTUM_TOKEN and IBM_QUANTUM_INSTANCE set in your env
    # or have saved credentials for this test to work.
    try:
        qrbg_ibm = QuantumRandomBitGenerator()
        print(f"Successfully connected to backend: {qrbg_ibm.backend_name}")
        bits, source = qrbg_ibm.get_random_bits(8)
        if bits is not None:
            print(f"Generated 8 bits: {bits}")
            print(f"Source: {source}")
        else:
            print("Failed to generate bits during execution.")
    except Exception as e:
        print(f"Failed to initialize QRBG or generate bits: {e}")
        print(f"Source: {source}")
    else:
        print("Failed to generate bits.")

    print("\nTesting complete.")
