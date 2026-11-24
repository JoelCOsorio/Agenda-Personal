"""Servicio de aplicación para Contactos y acciones externas por SO (PROC-05, RN-08, RN-13)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from agenda_app.application.ports.acciones_externas import ILanzadorAccionesExternas
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import IRepositorioContactos
from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.enums import PlataformaSO
from agenda_app.domain.exceptions import (
    AccionPlataformaNoSoportadaError,
    EntidadNoEncontradaError,
    ValidacionEntidadError,
)


class ServicioContactos:
    """Gestiona directorio de contactos, búsqueda y delegación mailto:/tel: según SO."""

    def __init__(
        self,
        repo_contactos: IRepositorioContactos,
        reloj: IReloj,
        plataforma: PlataformaSO,
        lanzador: ILanzadorAccionesExternas | None = None,
    ) -> None:
        self._repo = repo_contactos
        self._reloj = reloj
        self._plataforma = plataforma
        self._lanzador = lanzador

    def crear_contacto(
        self,
        *,
        nombre: str,
        telefono: str | None = None,
        correo: str | None = None,
        notas: str | None = None,
        etiqueta: str | None = None,
    ) -> Contacto:
        ahora = self._reloj.ahora_utc()
        contacto = Contacto(
            nombre=nombre,
            telefono=telefono,
            correo=correo,
            notas=notas,
            etiqueta=etiqueta,
            created_at=ahora,
            updated_at=ahora,
        )
        self._repo.guardar(contacto)
        return contacto

    def editar_contacto(
        self,
        contacto_id: UUID,
        *,
        nombre: str | None = None,
        telefono: str | None = None,
        correo: str | None = None,
        notas: str | None = None,
        etiqueta: str | None = None,
    ) -> Contacto:
        actual = self._repo.obtener_por_id(contacto_id)
        if actual is None:
            raise EntidadNoEncontradaError(f"Contacto {contacto_id} no encontrado.")

        editado = Contacto(
            id=actual.id,
            nombre=actual.nombre if nombre is None else nombre,
            telefono=actual.telefono if telefono is None else telefono,
            correo=actual.correo if correo is None else correo,
            notas=actual.notas if notas is None else notas,
            etiqueta=actual.etiqueta if etiqueta is None else etiqueta,
            created_at=actual.created_at,
            updated_at=self._reloj.ahora_utc(),
        )
        self._repo.guardar(editado)
        return editado

    def eliminar_contacto(self, contacto_id: UUID) -> None:
        """Elimina el contacto desvinculándolo sin borrar eventos ni tareas (RN-13)."""
        self._repo.eliminar(contacto_id)

    def obtener_contacto(self, contacto_id: UUID) -> Contacto | None:
        return self._repo.obtener_por_id(contacto_id)

    def obtener_varios(self, ids: Sequence[UUID]) -> list[Contacto]:
        return self._repo.obtener_varios(ids)

    def buscar(
        self,
        *,
        termino: str | None = None,
        etiqueta: str | None = None,
    ) -> list[Contacto]:
        return self._repo.buscar(termino=termino, etiqueta=etiqueta)

    def puede_llamar_en_plataforma_actual(self, contacto: Contacto) -> bool:
        return contacto.puede_llamar(self._plataforma)

    async def abrir_correo_contacto(self, contacto_id: UUID) -> bool:
        """Lanza el gestor de correo externo (mailto:) en Android, Windows y Linux (RN-08)."""
        contacto = self._repo.obtener_por_id(contacto_id)
        if contacto is None:
            raise EntidadNoEncontradaError(f"Contacto {contacto_id} no encontrado.")
        uri = contacto.generar_uri_correo()
        if uri is None:
            raise ValidacionEntidadError("El contacto no tiene un correo electrónico válido.")
        if self._lanzador is None:
            return False
        return await self._lanzador.abrir_uri(uri)

    async def llamar_contacto(self, contacto_id: UUID) -> bool:
        """Lanza la app de llamadas (tel:) únicamente en Android (RN-08)."""
        if self._plataforma != PlataformaSO.ANDROID:
            raise AccionPlataformaNoSoportadaError(
                f"RN-08: Las llamadas telefónicas no están disponibles en {self._plataforma.value}."
            )
        contacto = self._repo.obtener_por_id(contacto_id)
        if contacto is None:
            raise EntidadNoEncontradaError(f"Contacto {contacto_id} no encontrado.")
        uri = contacto.generar_uri_llamada(self._plataforma)
        if uri is None:
            raise ValidacionEntidadError("El contacto no tiene un número de teléfono válido.")
        if self._lanzador is None:
            return False
        return await self._lanzador.abrir_uri(uri)
