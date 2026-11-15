from pydantic import BaseModel, ConfigDict


class ORMRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
