class AcgxBaseError(Exception):
    def __init__(self, message):
        super().__init__(self)
        self.message = message

    def __str__(self):
        return self.message


class AcgxProxyClientParseError(AcgxBaseError):
    pass


class AcgxProxyClientImplementError(AcgxBaseError):
    pass
