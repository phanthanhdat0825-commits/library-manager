from dataclasses import dataclass


@dataclass
class Book:
    book_code: str
    title: str
    author: str = ""
    category: str = ""
    publisher: str = ""
    publish_year: int | None = None
    quantity: int = 1
    shelf: str = ""
    description: str = ""