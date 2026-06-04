from pydantic import BaseModel, field_validator


class TrackActivityBody(BaseModel):
    activity_type: str


class ViewDurationIn(BaseModel):
    duration_seconds: int

    @field_validator("duration_seconds")
    @classmethod
    def cap_duration(cls, v: int) -> int:
        return max(0, min(v, 3600))