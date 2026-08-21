export type UserRol = "admin_rrhh" | "gerencia_lectura" | "mandos_medios"

/** Etiquetas legibles de cada rol. Fuente única — la consumen configuración y el menú de usuario. */
export const ROL_LABEL: Record<UserRol, string> = {
  admin_rrhh: "Administrador de Capital Humano",
  gerencia_lectura: "Gerencia (lectura)",
  mandos_medios: "Mandos medios",
}

export interface UserInfo {
  id: string
  email: string
  username: string
  rol: UserRol
  nombre: string
  apellido: string
  must_change_password: boolean
}

export interface Session {
  access_token: string
  refresh_token: string
  user: UserInfo
}
