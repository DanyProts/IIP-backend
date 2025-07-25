from pydantic import BaseModel

class UserRegister(BaseModel):
    email: str
    firstName: str
    lastName: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str
