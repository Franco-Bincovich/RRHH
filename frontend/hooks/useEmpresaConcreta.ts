"use client"

import { useEffect, useState } from "react"

import { getEmpresaActivaId, subscribeEmpresaActiva } from "@/services/empresaStore"

/**
 * El texto que se le muestra a alguien de RRHH cuando la acción que quiere hacer necesita una
 * empresa concreta y el sidebar está en "Todas las empresas".
 *
 * 🔴 ES EL MISMO MENSAJE QUE EL DEL BACKEND, A PROPÓSITO Y CASI PALABRA POR PALABRA
 * (`backend/utils/empresa.py::require_empresa_id`, code `EMPRESA_ID_REQUIRED`). No se centraliza
 * en un lugar solo porque son dos procesos distintos, pero sí se mantienen iguales: si el aviso
 * de la pantalla y el error del servidor dijeran cosas distintas, el usuario que vea los dos
 * —porque llegó por otra puerta, o porque cambió la empresa entre que abrió el form y guardó—
 * creería que son dos problemas.
 *
 * 🚩 Disparador para volver sobre esto: que aparezca un tercer lugar que lo diga.
 */
export const MOTIVO_SIN_EMPRESA =
  "Elegí una empresa en el selector de arriba a la izquierda: esto se hace sobre una empresa " +
  "concreta y no sobre la vista consolidada."

/**
 * La empresa activa del sidebar, REACTIVA, y el motivo por el que una acción no se puede hacer
 * en modo consolidado.
 *
 * 🔴 POR QUÉ ES UN HOOK Y NO `getEmpresaActivaId()` SUELTO EN EL RENDER, que es lo que hacen ocho
 * pantallas hoy. Aquéllas lo leen UNA vez con `useState(() => getEmpresaActivaId())` y les
 * alcanza: lo usan para decidir si muestran la columna "Empresa", y el selector del sidebar
 * recarga los datos igual. Acá el valor decide si un BOTÓN se puede apretar, así que tiene que
 * seguir al selector: si alguien elige una empresa con el formulario abierto, el botón tiene que
 * habilitarse sin recargar la página. Por eso se suscribe al store.
 *
 * 🔴 Y POR QUÉ EL ESTADO INICIAL ES `null` EN VEZ DE LEER EL STORE EN EL PRIMER RENDER. El store
 * es `localStorage`, que el servidor no tiene: leerlo durante el render produce el mismatch de
 * hidratación que `hooks/useRol.ts` documenta. `null` es además el valor SEGURO en la dirección
 * que importa — significa "consolidado", así que el primer paint muestra el botón bloqueado con
 * su motivo y, si hay empresa, se habilita en el efecto. Al revés (asumir que hay empresa) el
 * botón aparecería habilitado un instante y fallaría con 400 al que llegue rápido.
 *
 * ⚠️ NO ES UNA BARRERA DE SEGURIDAD, igual que `useCanWrite`: el backend rechaza con 400
 * `EMPRESA_ID_REQUIRED` de todos modos. Lo que evita es ofrecer un botón que no puede funcionar.
 */
export function useEmpresaConcreta(): { empresaId: string | null; motivo: string | null } {
  const [empresaId, setEmpresaId] = useState<string | null>(null)

  useEffect(() => {
    setEmpresaId(getEmpresaActivaId())
    return subscribeEmpresaActiva(setEmpresaId)
  }, [])

  return { empresaId, motivo: empresaId ? null : MOTIVO_SIN_EMPRESA }
}
