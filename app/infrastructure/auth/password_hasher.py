from werkzeug.security import check_password_hash, generate_password_hash

from app.domain.ports.services import PasswordHasherPort


class WerkzeugPasswordHasher(PasswordHasherPort):
    def hash_password(self, plain_password: str) -> str:
        return generate_password_hash(plain_password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, plain_password)
