from dataclasses import dataclass


@dataclass
class Reader:
    reader_code: str
    name: str
    phone: str = ""
    email: str = ""
    class_name: str = ""