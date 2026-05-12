import base64
import json
import os

import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SimpleVault:
    """
    Mo phong envelope encryption pattern (thay the AWS KMS cho local dev).

    Architecture:
        Master Key (KEK) -> encrypts -> Data Key (DEK) -> encrypts -> Data
    """

    def __init__(self, master_key_path: str = ".vault_key"):
        self.master_key_path = master_key_path
        self.kek = self._load_or_create_kek()

    def _load_or_create_kek(self) -> bytes:
        """
        Load KEK tu environment variable (uu tien) hoac file.
        Neu khong co, generate moi va luu vao file (chi dung local dev).
        QUAN TRONG: Trong production, KEK phai luu trong HSM/KMS, khong phai file.
        """
        env_key = os.environ.get("MEDVIET_KEK")
        if env_key:
            return base64.b64decode(env_key)

        if os.path.exists(self.master_key_path):
            with open(self.master_key_path, "rb") as f:
                return base64.b64decode(f.read())
        else:
            kek = os.urandom(32)  # 256-bit key
            with open(self.master_key_path, "wb") as f:
                f.write(base64.b64encode(kek))
            os.chmod(self.master_key_path, 0o600)
            return kek

    def generate_dek(self) -> tuple[bytes, bytes]:
        """
        Generate mot Data Encryption Key (DEK) moi.
        Tra ve (plaintext_dek, encrypted_dek).
        Dung AESGCM de encrypt DEK bang KEK.
        """
        plaintext_dek = os.urandom(32)
        aesgcm = AESGCM(self.kek)
        nonce = os.urandom(12)
        encrypted_dek = nonce + aesgcm.encrypt(nonce, plaintext_dek, None)
        return plaintext_dek, encrypted_dek

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        """
        Decrypt encrypted DEK bang KEK.
        Tra ve plaintext DEK.
        """
        nonce = encrypted_dek[:12]
        ciphertext = encrypted_dek[12:]
        aesgcm = AESGCM(self.kek)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_data(self, plaintext: str) -> dict:
        """
        Implement envelope encryption.
        1. Generate DEK moi
        2. Encrypt data bang plaintext DEK
        3. Xoa plaintext DEK khoi memory
        4. Tra ve dict chua encrypted_dek va ciphertext (base64 encoded)
        """
        plaintext_dek, encrypted_dek = self.generate_dek()
        aesgcm = AESGCM(plaintext_dek)
        nonce = os.urandom(12)
        # AESGCM.encrypt returns ciphertext || auth_tag (16 bytes)
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        del plaintext_dek

        return {
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            # Store nonce || ciphertext_with_tag so decrypt knows the nonce
            "ciphertext": base64.b64encode(nonce + ciphertext_with_tag).decode(),
            "algorithm": "AES-256-GCM",
        }

    def decrypt_data(self, encrypted_payload: dict) -> str:
        """
        Decrypt data tu envelope encryption payload.
        1. Decrypt DEK bang KEK
        2. Decrypt data bang DEK
        3. Tra ve plaintext string
        """
        encrypted_dek = base64.b64decode(encrypted_payload["encrypted_dek"])
        ciphertext_with_tag = base64.b64decode(encrypted_payload["ciphertext"])
        plaintext_dek = self.decrypt_dek(encrypted_dek)
        nonce = ciphertext_with_tag[:12]
        cipher = ciphertext_with_tag[12:]
        aesgcm = AESGCM(plaintext_dek)
        plaintext = aesgcm.decrypt(nonce, cipher, None)
        del plaintext_dek
        return plaintext.decode("utf-8")

    def encrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Encrypt mot cot trong DataFrame.
        Thay the gia tri goc bang JSON string cua encrypted payload.
        """
        df = df.copy()
        df[column] = df[column].apply(
            lambda x: json.dumps(self.encrypt_data(str(x)))
        )
        return df

    def decrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Decrypt mot cot da ma hoa trong DataFrame.
        Giai ma tu JSON string cua encrypted payload.
        """
        df = df.copy()
        df[column] = df[column].apply(
            lambda x: self.decrypt_data(json.loads(x))
        )
        return df
