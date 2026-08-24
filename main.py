from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from psycopg import errors as psycopg_errors

from database import inicializar_base_datos, obtener_conexion
from models import (
    HurtoActualizar,
    HurtoCrear,
    HurtoRespuesta,
    Token,
    TipoHurtoActualizar,
    TipoHurtoCrear,
    TipoHurtoRespuesta,
    UsuarioRegistro,
    UsuarioRespuesta,
)
from auth import (
    crear_token_acceso,
    hash_password,
    obtener_usuario_actual,
    verificar_password,
)

app = FastAPI(
    title="API de Registro de Hurtos",
    description="API REST para el registro y consulta de denuncias de hurtos, con autenticación JWT.",
    version="1.0.0",
)


@app.on_event("startup")
def evento_inicio():
    inicializar_base_datos()


# ==================== AUTENTICACIÓN ====================

@app.post("/registro", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED, tags=["Autenticación"])
def registrar_usuario(usuario: UsuarioRegistro):
    password_hash = hash_password(usuario.password)
    try:
        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO usuarios (username, password_hash) VALUES (%s, %s) RETURNING id, username",
                    (usuario.username, password_hash),
                )
                nuevo_usuario = cur.fetchone()
            conn.commit()
    except psycopg_errors.UniqueViolation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya existe")

    return nuevo_usuario


@app.post("/login", response_model=Token, tags=["Autenticación"])
def iniciar_sesion(form_data: OAuth2PasswordRequestForm = Depends()):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash FROM usuarios WHERE username = %s", (form_data.username,))
            usuario = cur.fetchone()

    if usuario is None or not verificar_password(form_data.password, usuario["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_token_acceso({"sub": usuario["username"]})
    return {"access_token": token, "token_type": "bearer"}


# ==================== TIPO_HURTO ====================

@app.post(
    "/tipos-hurto",
    response_model=TipoHurtoRespuesta,
    status_code=status.HTTP_201_CREATED,
    tags=["Tipo de Hurto"],
)
def crear_tipo_hurto(tipo: TipoHurtoCrear, usuario_actual: dict = Depends(obtener_usuario_actual)):
    try:
        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tipo_hurto (nombre) VALUES (%s) RETURNING id_tipo, nombre",
                    (tipo.nombre,),
                )
                nuevo_tipo = cur.fetchone()
            conn.commit()
    except psycopg_errors.UniqueViolation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un tipo de hurto con ese nombre")

    return nuevo_tipo


@app.get("/tipos-hurto", response_model=List[TipoHurtoRespuesta], tags=["Tipo de Hurto"])
def listar_tipos_hurto(usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_tipo, nombre FROM tipo_hurto ORDER BY id_tipo")
            return cur.fetchall()


@app.get("/tipos-hurto/{id_tipo}", response_model=TipoHurtoRespuesta, tags=["Tipo de Hurto"])
def obtener_tipo_hurto(id_tipo: int, usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_tipo, nombre FROM tipo_hurto WHERE id_tipo = %s", (id_tipo,))
            tipo = cur.fetchone()

    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de hurto no encontrado")

    return tipo


@app.put("/tipos-hurto/{id_tipo}", response_model=TipoHurtoRespuesta, tags=["Tipo de Hurto"])
def actualizar_tipo_hurto(
    id_tipo: int, tipo: TipoHurtoActualizar, usuario_actual: dict = Depends(obtener_usuario_actual)
):
    try:
        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tipo_hurto SET nombre = %s WHERE id_tipo = %s RETURNING id_tipo, nombre",
                    (tipo.nombre, id_tipo),
                )
                tipo_actualizado = cur.fetchone()
            conn.commit()
    except psycopg_errors.UniqueViolation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un tipo de hurto con ese nombre")

    if tipo_actualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de hurto no encontrado")

    return tipo_actualizado


@app.delete("/tipos-hurto/{id_tipo}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tipo de Hurto"])
def eliminar_tipo_hurto(id_tipo: int, usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM hurto WHERE id_tipo_hurto = %s", (id_tipo,))
            total = cur.fetchone()["total"]

            if total > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar: existen hurtos registrados con este tipo",
                )

            cur.execute("DELETE FROM tipo_hurto WHERE id_tipo = %s RETURNING id_tipo", (id_tipo,))
            eliminado = cur.fetchone()
        conn.commit()

    if eliminado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de hurto no encontrado")


# ==================== HURTO ====================

CONSULTA_HURTO_CON_TIPO = """
    SELECT h.id, h.id_tipo_hurto, t.nombre AS nombre_tipo_hurto,
           h.denunciante, h.direccion, h.fecha_hurto, h.fecha_registro
    FROM hurto h
    JOIN tipo_hurto t ON h.id_tipo_hurto = t.id_tipo
"""


@app.post("/hurtos", response_model=HurtoRespuesta, status_code=status.HTTP_201_CREATED, tags=["Hurto"])
def crear_hurto(hurto: HurtoCrear, usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_tipo FROM tipo_hurto WHERE id_tipo = %s", (hurto.id_tipo_hurto,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El tipo de hurto indicado no existe")

            cur.execute(
                """
                INSERT INTO hurto (id_tipo_hurto, denunciante, direccion, fecha_hurto)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (hurto.id_tipo_hurto, hurto.denunciante, hurto.direccion, hurto.fecha_hurto),
            )
            nuevo_id = cur.fetchone()["id"]
            conn.commit()

            cur.execute(CONSULTA_HURTO_CON_TIPO + " WHERE h.id = %s", (nuevo_id,))
            resultado = cur.fetchone()

    return resultado


@app.get("/hurtos", response_model=List[HurtoRespuesta], tags=["Hurto"])
def listar_hurtos(usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(CONSULTA_HURTO_CON_TIPO + " ORDER BY h.id")
            return cur.fetchall()


@app.get("/hurtos/{id_hurto}", response_model=HurtoRespuesta, tags=["Hurto"])
def obtener_hurto(id_hurto: int, usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(CONSULTA_HURTO_CON_TIPO + " WHERE h.id = %s", (id_hurto,))
            hurto = cur.fetchone()

    if hurto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hurto no encontrado")

    return hurto


@app.put("/hurtos/{id_hurto}", response_model=HurtoRespuesta, tags=["Hurto"])
def actualizar_hurto(
    id_hurto: int, hurto: HurtoActualizar, usuario_actual: dict = Depends(obtener_usuario_actual)
):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_tipo FROM tipo_hurto WHERE id_tipo = %s", (hurto.id_tipo_hurto,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El tipo de hurto indicado no existe")

            cur.execute(
                """
                UPDATE hurto
                SET id_tipo_hurto = %s, denunciante = %s, direccion = %s, fecha_hurto = %s
                WHERE id = %s
                RETURNING id
                """,
                (hurto.id_tipo_hurto, hurto.denunciante, hurto.direccion, hurto.fecha_hurto, id_hurto),
            )
            actualizado = cur.fetchone()
            conn.commit()

            if actualizado is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hurto no encontrado")

            cur.execute(CONSULTA_HURTO_CON_TIPO + " WHERE h.id = %s", (id_hurto,))
            resultado = cur.fetchone()

    return resultado


@app.delete("/hurtos/{id_hurto}", status_code=status.HTTP_204_NO_CONTENT, tags=["Hurto"])
def eliminar_hurto(id_hurto: int, usuario_actual: dict = Depends(obtener_usuario_actual)):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hurto WHERE id = %s RETURNING id", (id_hurto,))
            eliminado = cur.fetchone()
        conn.commit()

    if eliminado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hurto no encontrado")
