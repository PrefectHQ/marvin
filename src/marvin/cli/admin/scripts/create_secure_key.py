import secrets
import string


def create_secure_key(length=50):
    alphabet = string.ascii_letters + string.digits + "_"
    secure_key = "".join(secrets.choice(alphabet) for _ in range(length))
    return secure_key
