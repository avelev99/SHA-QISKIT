import hashlib
import struct
import math
import logging
from qrbg import QuantumRandomBitGenerator

# Configure logging (can be configured externally as well)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- SHA-256 Constants and Helper Functions ---
# (Adapted from Python's hashlib implementation reference or FIPS 180-4)

# Initial hash values (H0-H7)
H = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]

# Round constants (K0-K63)
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

# Logical functions
def rotr(x, n):
    """Rotate right (circular shift right) on 32 bits."""
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def shr(x, n):
    """Shift right on 32 bits."""
    return (x >> n) & 0xFFFFFFFF

def sigma0(x):
    """SHA-256 Sigma0 function."""
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)

def sigma1(x):
    """SHA-256 Sigma1 function."""
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)

def Sigma0(x):
    """SHA-256 Big Sigma0 function."""
    return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)

def Sigma1(x):
    """SHA-256 Big Sigma1 function."""
    return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)

def Ch(x, y, z):
    """SHA-256 Choose function."""
    return (x & y) ^ (~x & z)

def Maj(x, y, z):
    """SHA-256 Majority function."""
    return (x & y) ^ (x & z) ^ (y & z)

# --- QSHA Implementation ---

def _preprocess_message(message):
    """Pads the message according to SHA-256 standards."""
    message_len_bits = len(message) * 8
    message += b'\x80' # Append '1' bit (represented as byte 0x80)
    # Append '0' bits until message length in bits is congruent to 448 (mod 512)
    message += b'\x00' * ((56 - (len(message) % 64)) % 64)
    # Append original message length as 64-bit big-endian integer
    message += struct.pack('>Q', message_len_bits)
    return message

def _bits_to_ints(bit_string):
    """Converts a string of '0's and '1's into a list of 32-bit integers."""
    ints = []
    chunk_size = 32
    if len(bit_string) % chunk_size != 0:
        raise ValueError("Bit string length must be a multiple of 32")
    for i in range(0, len(bit_string), chunk_size):
        chunk = bit_string[i:i+chunk_size]
        ints.append(int(chunk, 2))
    return ints

def qsha256(input_data: bytes, qrbg_instance: QuantumRandomBitGenerator = None):
    """
    Computes the QSHA-256 hash of the input data using a real IBM Quantum backend.

    Args:
        input_data (bytes): The message to hash.
        qrbg_instance (QuantumRandomBitGenerator, optional): An existing QRBG instance.
            If None, a new one will be created (requires IBM Q setup).

    Returns:
        tuple: A tuple containing:
            - str: The 64-character hexadecimal QSHA-256 digest.
            - str: The name of the backend used for randomness generation.
            Returns (None, backend_name) if hashing fails (e.g., QRBG error).
    """
    # Create or use the QRBG instance. It will raise an error if IBM Q connection fails.
    try:
        if qrbg_instance is None:
            logging.info("Creating new QuantumRandomBitGenerator instance for QSHA (requires IBM Q).")
            qrbg = QuantumRandomBitGenerator()
        else:
            qrbg = qrbg_instance
    except Exception as e:
        logging.error(f"Failed to initialize QuantumRandomBitGenerator: {e}")
        return None, "Initialization Error" # Indicate failure reason

    # 1. Get Quantum Salt
    salt_bits = 256
    logging.info(f"Requesting {salt_bits} bits for quantum salt...")
    salt_string, backend_name = qrbg.get_random_bits(salt_bits)

    if salt_string is None:
        logging.error("Failed to obtain quantum salt from QRBG.")
        return None, backend_name # Propagate backend name even on failure

    logging.info(f"Obtained {salt_bits}-bit salt from {backend_name}.")
    # logging.debug(f"Salt: {salt_string}") # Optional: log the salt if needed

    try:
        salt_ints = _bits_to_ints(salt_string)
        if len(salt_ints) != 8:
             # This should not happen if get_random_bits works correctly
             raise ValueError(f"Salt conversion resulted in {len(salt_ints)} ints, expected 8.")
    except ValueError as e:
        logging.error(f"Error processing salt string: {e}")
        return None, backend_name

    # 2. Initialize hash values and apply salt
    current_h = list(H) # Make a copy of initial values
    logging.debug(f"Initial H: {[hex(h) for h in current_h]}")
    logging.debug(f"Salt Integers: {[hex(s) for s in salt_ints]}")

    for i in range(8):
        current_h[i] = (current_h[i] ^ salt_ints[i]) & 0xFFFFFFFF
    logging.info("Applied quantum salt to initial hash values.")
    logging.debug(f"Salted H: {[hex(h) for h in current_h]}")


    # 3. Preprocess the message
    padded_message = _preprocess_message(input_data)
    logging.debug(f"Padded message length: {len(padded_message)} bytes")

    # 4. Process message in 512-bit (64-byte) chunks
    for i in range(0, len(padded_message), 64):
        chunk = padded_message[i:i+64]
        w = list(struct.unpack('>16L', chunk)) # Unpack chunk into 16 32-bit words (big-endian)
        logging.debug(f"Processing chunk {i//64}")

        # Extend the 16 words into 64 words (message schedule)
        for t in range(16, 64):
            s0 = Sigma0(w[t-15])
            s1 = Sigma1(w[t-2])
            w.append((w[t-16] + s0 + w[t-7] + s1) & 0xFFFFFFFF)

        # Initialize working variables for this chunk
        a, b, c, d, e, f, g, h = current_h

        # Compression function main loop (64 rounds)
        for t in range(64):
            T1 = (h + sigma1(e) + Ch(e, f, g) + K[t] + w[t]) & 0xFFFFFFFF
            T2 = (sigma0(a) + Maj(a, b, c)) & 0xFFFFFFFF
            h = g
            g = f
            f = e
            e = (d + T1) & 0xFFFFFFFF
            d = c
            c = b
            b = a
            a = (T1 + T2) & 0xFFFFFFFF

        # Update hash values for this chunk
        current_h[0] = (current_h[0] + a) & 0xFFFFFFFF
        current_h[1] = (current_h[1] + b) & 0xFFFFFFFF
        current_h[2] = (current_h[2] + c) & 0xFFFFFFFF
        current_h[3] = (current_h[3] + d) & 0xFFFFFFFF
        current_h[4] = (current_h[4] + e) & 0xFFFFFFFF
        current_h[5] = (current_h[5] + f) & 0xFFFFFFFF
        current_h[6] = (current_h[6] + g) & 0xFFFFFFFF
        current_h[7] = (current_h[7] + h) & 0xFFFFFFFF

    # 5. Produce final hash value
    final_hash_hex = ''.join(f'{val:08x}' for val in current_h)
    logging.info("QSHA-256 computation complete.")

    return final_hash_hex, backend_name


# Example Usage (for testing)
if __name__ == "__main__":
    print("Testing QSHA-256...")

    message1 = b"Hello, Quantum World!"
    message2 = b"Hello, Quantum World!" # Same message
    message3 = b"Different message."

    # Example Usage (for testing - requires IBM Q setup)
    print("\n--- Testing QSHA-256 (Requires IBM Quantum Setup) ---")

    message1 = b"Hello, Quantum World!"
    message2 = b"Hello, Quantum World!" # Same message
    message3 = b"Different message."

    try:
        # Create one QRBG instance for the tests
        qrbg_real = QuantumRandomBitGenerator()
        print(f"Using backend: {qrbg_real.backend_name}")

        # Run 1
        print("\n--- Run 1 ---")
        digest1, source1 = qsha256(message1, qrbg_instance=qrbg_real)
        if digest1:
            print(f"Message: {message1}")
            print(f"Digest:  {digest1}")
            print(f"Source:  {source1}")

        # Run 2 (same message, same QRBG instance - should still differ due to new salt)
        print("\n--- Run 2 (Same Message) ---")
        digest2, source2 = qsha256(message2, qrbg_instance=qrbg_real)
        if digest2:
            print(f"Message: {message2}")
            print(f"Digest:  {digest2}")
            print(f"Source:  {source2}")
            if digest1: # Check if first digest was generated
                 print(f"Digests equal: {digest1 == digest2}") # Expected: False

        # Run 3 (different message)
        print("\n--- Run 3 (Different Message) ---")
        digest3, source3 = qsha256(message3, qrbg_instance=qrbg_real)
        if digest3:
            print(f"Message: {message3}")
            print(f"Digest:  {digest3}")
            print(f"Source:  {source3}")

    except Exception as e:
        print(f"\nError during QSHA testing (likely QRBG initialization failed): {e}")
        print("Ensure IBM Quantum Token/Instance are set or credentials saved.")

    print("\nQSHA testing complete.")
