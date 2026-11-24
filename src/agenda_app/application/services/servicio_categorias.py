"""Servicio de aplicación para Categorías y Subcategorías (PROC-06, RF-21, RF-22, RN-09)."""

from __future__ import annotations

from uuid import UUID

from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import IRepositorioCategorias
from agenda_app.domain.entities.categoria import Categoria, Subcategoria
from agenda_app.domain.exceptions import (
    EntidadNoEncontradaError,
    JerarquiaCategoriaInvalidaError,
)


class ServicioCategorias:
    """Gestiona categorías principales y subcategorías (máximo 2 niveles — RN-09)."""

    def __init__(
        self,
        repo_categorias: IRepositorioCategorias,
        reloj: IReloj,
    ) -> None:
        self._repo = repo_categorias
        self._reloj = reloj

    def crear_categoria(
        self,
        *,
        nombre: str,
        color_hex: str = "#3B82F6",
        icono: str | None = None,
    ) -> Categoria:
        ahora = self._reloj.ahora_utc()
        categoria = Categoria(
            nombre=nombre,
            color_hex=color_hex,
            icono=icono,
            created_at=ahora,
            updated_at=ahora,
        )
        self._repo.guardar_categoria(categoria)
        return categoria

    def editar_categoria(
        self,
        categoria_id: UUID,
        *,
        nombre: str | None = None,
        color_hex: str | None = None,
        icono: str | None = None,
    ) -> Categoria:
        actual = self._repo.obtener_categoria(categoria_id)
        if actual is None:
            raise EntidadNoEncontradaError(f"Categoría {categoria_id} no encontrada.")
        actualizada = Categoria(
            id=actual.id,
            nombre=actual.nombre if nombre is None else nombre,
            color_hex=actual.color_hex if color_hex is None else color_hex,
            icono=actual.icono if icono is None else icono,
            created_at=actual.created_at,
            updated_at=self._reloj.ahora_utc(),
        )
        self._repo.guardar_categoria(actualizada)
        return actualizada

    def eliminar_categoria(self, categoria_id: UUID) -> None:
        """Elimina una categoría padre conservando eventos y tareas (pasan a Sin categoría, RN-13)."""
        self._repo.eliminar_categoria(categoria_id)

    def listar_categorias(self) -> list[Categoria]:
        return self._repo.listar_categorias()

    def crear_subcategoria(
        self,
        *,
        categoria_id: UUID,
        nombre: str,
        color_hex: str | None = None,
    ) -> Subcategoria:
        if self._repo.obtener_categoria(categoria_id) is None:
            raise JerarquiaCategoriaInvalidaError(
                f"RN-09: No existe la categoría padre {categoria_id}."
            )
        ahora = self._reloj.ahora_utc()
        sub = Subcategoria(
            categoria_id=categoria_id,
            nombre=nombre,
            color_hex=color_hex,
            created_at=ahora,
            updated_at=ahora,
        )
        self._repo.guardar_subcategoria(sub)
        return sub

    def eliminar_subcategoria(self, subcategoria_id: UUID) -> None:
        """Elimina la subcategoría manteniendo la categoría padre en eventos/tareas (RN-13)."""
        self._repo.eliminar_subcategoria(subcategoria_id)

    def listar_subcategorias(self, categoria_id: UUID | None = None) -> list[Subcategoria]:
        return self._repo.listar_subcategorias(categoria_id)

    def validar_jerarquia(
        self,
        categoria_id: UUID | None,
        subcategoria_id: UUID | None,
    ) -> None:
        """Verifica RN-09: si se indica subcategoria_id, debe pertenecer a categoria_id."""
        if subcategoria_id is None:
            return
        if categoria_id is None:
            raise JerarquiaCategoriaInvalidaError(
                "RN-09: Para asignar una subcategoría se debe indicar su categoría padre."
            )
        if not self._repo.subcategoria_pertenece_a(subcategoria_id, categoria_id):
            raise JerarquiaCategoriaInvalidaError(
                "RN-09: La subcategoría seleccionada no pertenece a la categoría padre."
            )
