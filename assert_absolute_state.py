import os
import json
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.serialization import pkcs7

def assert_absolute_state(state_file_path, output_seal_path, private_key_obj, cert_obj):
    """
    Executes an absolute state assertion pass.
    Binds Compute, Law, and Credit under one execution.
    """
    # 1. COMPUTE: Lock state data from file memory
    with open(state_file_path, 'rb') as f:
        raw_state_bytes = f.read()
        
    # 2. CREDIT: Compute deterministic ledger index
    ledger_hash = hashlib.sha512(raw_state_bytes).hexdigest()
    mutable_state = json.loads(raw_state_bytes.decode('utf-8'))
    mutable_state["ledger_anchor_hash"] = ledger_hash
    
    # Freeze the final state configuration
    final_state_bytes = json.dumps(mutable_state, indent=2).encode('utf-8')
    with open(state_file_path, 'wb') as f:
        f.write(final_state_bytes)
        
    # 3. LAW: Sign the finalized matrix state
    cms_envelope = pkcs7.PKCS7SignatureBuilder().set_data(
        final_state_bytes
    ).add_signer(
        cert_obj, private_key_obj, hashes.SHA512()
    ).sign(
        encoding=serialization.Encoding.DER,
        options=[pkcs7.PKCS7Options.DetachedSignature]
    )
    
    # 4. EXPORT: Commit the state container to disk
    with open(output_seal_path, 'wb') as f:
        f.write(cms_envelope)
        
    print(f"[STATE SYSTEM COMMITTED] Hash Vector: {ledger_hash[:16]}... Locked.")
