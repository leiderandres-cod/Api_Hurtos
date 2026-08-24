import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

from database import obtener_conexion

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)


def crear_token_acceso(datos: dict) -> str:
    datos_codificar = datos.copy()
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    datos_codificar.update({"exp": expira})
    return jwt.encode(datos_codificar, SECRET_KEY, algorithm=ALGORITHM)


def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> dict:
    credenciales_excepcion = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credenciales_excepcion
    except JWTError:
        raise credenciales_excepcion

    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM usuarios WHERE username = %s", (username,))
            usuario = cur.fetchone()

    if usuario is None:
        raise credenciales_excepcion

    return usuario
