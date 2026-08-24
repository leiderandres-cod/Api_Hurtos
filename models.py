from datetime import date, datetime
from pydantic import BaseModel, Field


# ---------- Usuarios / Autenticación ----------

class UsuarioRegistro(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UsuarioRespuesta(BaseModel):
    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Tipo_Hurto ----------

class TipoHurtoCrear(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100, examples=["Hurto Vehiculo"])


class TipoHurtoActualizar(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)


class TipoHurtoRespuesta(BaseModel):
    id_tipo: int
    nombre: str


# ---------- Hurto ----------

class HurtoCrear(BaseModel):
    id_tipo_hurto: int
    denunciante: str = Field(..., min_length=2, max_length=150)
    direccion: str = Field(..., min_length=2, max_length=255)
    fecha_hurto: date


class HurtoActualizar(BaseModel):
    id_tipo_hurto: int
    denunciante: str = Field(..., min_length=2, max_length=150)
    direccion: str = Field(..., min_length=2, max_length=255)
    fecha_hurto: date


class HurtoRespuesta(BaseModel):
    id: int
    id_tipo_hurto: int
    nombre_tipo_hurto: str
    denunciante: str
    direccion: str
    fecha_hurto: date
    fecha_registro: datetime
