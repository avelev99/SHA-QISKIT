#!/usr/bin/env python
import argparse
import sys
import logging
import os

# Add the directory containing qsha and qrbg to the Python path
# This makes the script runnable from anywhere, assuming qsha.py and qrbg.py
# are in the same directory as qsha_cli.py
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from qsha import qsha256
    from qrbg import QuantumRandomBitGenerator # Although qsha handles instance creation
except ImportError as e:
    print(f"Error: Failed to import required modules (qsha, qrbg). Ensure they are in the same directory or Python path: {e}", file=sys.stderr)
    sys.exit(1)

# Configure logging for the CLI script itself
# Note: qrbg and qsha might have their own logging setup
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - CLI - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(
        description="Compute a Quantum-Salted Hash (QSHA-256) digest using a real IBM Quantum backend.",
        epilog="Requires configured IBM Quantum credentials. Reads message from stdin if no message argument is provided."
    )
    parser.add_argument(
        'message',
        nargs='?',
        type=str,
        help="Optional message string to hash. If omitted, reads from stdin."
    )
    parser.add_argument(
        '--bits',
        type=int,
        default=256,
        help="Desired hash length in bits. Currently only 256 is supported. (Default: 256)"
    )
    # Removed --simulator argument
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging (INFO level) for QSHA/QRBG operations."
    )

    args = parser.parse_args()

    # --- Configure Logging Level ---
    if args.verbose:
        # Set the root logger level, affecting qsha and qrbg if they use the root logger
        logging.getLogger().setLevel(logging.INFO)
        logging.info("Verbose logging enabled.")
    else:
        # Keep default (WARNING) or set explicitly if needed
        logging.getLogger().setLevel(logging.WARNING)


    # --- Validate Arguments ---
    if args.bits != 256:
        print(f"Error: Currently, only --bits 256 is supported by the QSHA implementation.", file=sys.stderr)
        sys.exit(1)

    # --- Get Input Message ---
    if args.message is not None:
        input_string = args.message
        logging.info("Read message from command line argument.")
    else:
        if sys.stdin.isatty():
            print("Enter message (end with Ctrl+D on Unix/Linux, Ctrl+Z+Enter on Windows):", file=sys.stderr)
        input_string = sys.stdin.read()
        logging.info("Read message from standard input.")
        # Remove trailing newline often added by echo or interactive input
        if input_string.endswith('\n'):
            input_string = input_string[:-1]


    # Ensure message is bytes
    try:
        input_bytes = input_string.encode('utf-8')
    except Exception as e:
         print(f"Error encoding input message to UTF-8: {e}", file=sys.stderr)
         sys.exit(1)

    # --- Compute QSHA Hash ---
    print(f"Computing QSHA-{args.bits} hash using IBM Quantum...", file=sys.stderr)
    # qsha256 will now handle QRBG creation, which requires IBM Q connection.
    # We wrap this in a try-except block to catch potential initialization or runtime errors.
    try:
        digest, source = qsha256(input_bytes) # No force_simulator needed

        # --- Output Results ---
        if digest:
            # Correctly indented block for success case
            print(digest, file=sys.stdout) # Print digest to stdout
            print(f"Randomness Source: {source}", file=sys.stderr) # Print source to stderr
            sys.exit(0)
        else:
            # This case might happen if QRBG initializes but fails during bit generation
            print(f"Error: Failed to compute QSHA hash. Check logs for details.", file=sys.stderr)
            print(f"Last known source attempt: {source}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        # Catch errors during QRBG initialization or qsha256 execution
        print(f"\nError: An exception occurred during QSHA processing.", file=sys.stderr)
        print(f"Ensure IBM Quantum credentials are correctly configured (see README.md).", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

# Keep only one correctly placed main execution block
if __name__ == "__main__":
    main()
