class DocxReadError(ValueError):
    """Base error for a supported document that cannot be read safely."""


class InvalidDocxError(DocxReadError):
    pass


class EncryptedDocxError(DocxReadError):
    pass


class UnsupportedDocxError(DocxReadError):
    pass
