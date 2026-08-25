import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AVISO_CATALOGO_GLOBAL } from "./_avisos"
import { UsuariosTable } from "./UsuariosTable"

/**
 * El patrón del bloque B sobre /usuarios: **otro caso sin filtros**. `GET /api/usuarios` no
 * acepta un solo Query y devuelve la lista entera, así que (a), (b) y (d) NO APLICAN y este
 * archivo lo dice en vez de simularlos.
 *
 * Lo que sí se verifica es (c) —la tabla conserva su encabezado en los tres estados—, que el
 * vacío genérico del patrón SÍ es verdad para quien mira esta pantalla, y que la pantalla dice
 * que un usuario no pertenece a ninguna empresa.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · que el esqueleto declarara sus propias columnas.
 *   · que alguien agregara un chevron "a la ficha del usuario": esa ruta NO EXISTE.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "usuarios", "page.tsx")

const USUARIOS = [
  { id: "u1", nombre: "Ana", apellido: "Pérez", email: "ana@k.com", username: "aperez", rol: "admin_rrhh" },
] as Parameters<typeof UsuariosTable>[0]["usuarios"]

function tabla(props: Partial<Parameters<typeof UsuariosTable>[0]> = {}) {
  return renderToStaticMarkup(
    <UsuariosTable
      usuarios={[]} loading={false} error={false}
      onRetry={() => {}} onDelete={() => {}} deletingId={null}
      {...props}
    />,
  )
}

describe("(c) el encabezado sigue puesto en los tres estados", () => {
  it("con datos", () => {
    const html = tabla({ usuarios: USUARIOS })
    expect(html).toContain("<thead")
    for (const columna of ["Nombre", "Apellido", "Email", "Usuario", "Rol"]) {
      expect(html, `desapareció la columna ${columna}`).toContain(columna)
    }
    // El rol se muestra con su etiqueta legible, no con el valor crudo del backend.
    expect(html).not.toContain("admin_rrhh")
  })

  it("vacío: el bloque es una fila de la tabla, no un panel que la reemplaza", () => {
    const html = tabla({ accionVacio: <button>Crear usuario</button> })
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="6"')
    expect(html).toContain("Todavía no hay usuarios")
    expect(html).toContain("Crear usuario")
    expect(html).not.toContain("Limpiar todo")
  })

  it("🔴 el vacío genérico del patrón ES verdad para quien puede cargar el primero", () => {
    /*
     * La regla del bloque dice que "Cuando se cargue el primero va a aparecer acá" sólo vale si
     * el usuario de esa pantalla PUEDE cargarlo.
     *
     * 🔴 ESTE TEST CAMBIÓ EL 25/8/2026 Y HAY QUE LEER POR QUÉ. Afirmaba que la página tenía el
     * literal `puede(r, "usuarios", "write")`, o sea que **exigía por escrito el guard admin-only
     * que resultó ser el bug**: rebotaba a `gerencia_lectura` en contra del modelo de permisos y
     * del backend, que ya le sirve el listado a ese rol. Un test que fija una divergencia la
     * vuelve intocable — es el mismo caso que `dialog.test.tsx`, que protegía la regresión de los
     * 20 modales con `max-h-[90vh]` hasta que se dio vuelta.
     *
     * Lo que se afirma ahora es la CONDICIÓN real: el texto genérico se muestra cuando hay una
     * acción de alta, y la acción sólo llega con permiso de ESCRITURA (`esAdmin`). A quien sólo
     * lee, la página le pasa `accionVacio={undefined}`.
     */
    expect(tabla({ accionVacio: <button>Crear usuario</button> }))
      .toContain("Cuando se cargue el primero va a aparecer acá")
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).toContain('const esAdmin = rol !== null && puede(rol, "usuarios", "write")')
    expect(pagina).toContain("const crearBtn = esAdmin ?")
    // Y el rebote NO vuelve: quién entra lo decide el AuthGuard, como en todas las demás.
    // Se busca la LLAMADA (`router.replace(`) y no el nombre: el docstring de la página menciona
    // `router.replace` en prosa para explicar qué se sacó, y esa explicación tiene que sobrevivir.
    expect(pagina).not.toContain("router.replace(")
  })

  it("cargando: el esqueleto tiene la MISMA cantidad de columnas que la tabla", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 6)
    expect(cargando).toContain("animate-shimmer")
  })

  it("la única acción de fila es eliminar, y está SIEMPRE visible", () => {
    // 🔴 NO se inventó un chevron "a la ficha del usuario": esa pantalla no existe (no hay ruta
    // `/usuarios/[id]` ni `GET /{user_id}` en el router). Un chevron a una ruta inexistente es
    // peor que ninguno.
    const html = tabla({ usuarios: USUARIOS })
    expect(html).toContain("Eliminar Ana Pérez")
    expect(html).not.toContain("/usuarios/u1")
  })
})

describe("🔴 la pantalla DICE que un usuario no pertenece a una empresa", () => {
  it("el aviso viaja al subtítulo del encabezado", () => {
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).toContain("AVISO_CATALOGO_GLOBAL")
    expect(pagina).toMatch(/description=\{[\s\S]{0,400}?AVISO_CATALOGO_GLOBAL/)
    // Y dice el corolario, que es lo que nadie puede deducir mirando la tabla: cada acceso
    // alcanza a TODAS las empresas del grupo.
    expect(AVISO_CATALOGO_GLOBAL).toContain("todas las empresas del grupo")
  })

  it("(a) (b) (d) NO APLICAN: la pantalla no filtra ni pagina", () => {
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).not.toContain("<FiltersBar")
    expect(pagina).not.toContain("<Pagination")
    // Contracara: el archivo leído es el que se cree.
    expect(pagina).toContain("<UsuariosTable")
  })
})
