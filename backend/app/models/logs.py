from pydantic import BaseModel


class LogResult(BaseModel):
    service: str
    lines: list[str]
    truncated: bool = False
