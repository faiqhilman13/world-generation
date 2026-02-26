from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionBootstrapResponse(BaseModel):
    sid: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
