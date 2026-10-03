"""Privacy-safe, machine-readable failures."""


class MoneyWizError(ValueError):
    """Only fixed operational/schema context belongs in these messages."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}
