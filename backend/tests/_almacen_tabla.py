"""
Doble en memoria de `supabase_admin` para repos de tabla plana (sin embeds).

Helper, no test. Lo comparten `test_clientes_catalogo` (el repo solo) y `test_clientes_abm`
(el service sobre el repo REAL). Una sola copia a propósito: dos fakes de la misma tabla que se
separen darían dos comportamientos distintos para el mismo repo, y el test que use el permisivo
pasaría con el bug puesto.

## 🔴 LAS DOS COSAS QUE LO HACEN CAPAZ DE DESMENTIR ALGO

**1. `eq()` ACUMULA los filtros.** Los repos con barrera de empresa encadenan `.eq("id", …)` y
después `.eq("empresa_id", …)`. Un doble que se quedara con el ÚLTIMO filtro —o peor, que
aceptara `empresa_id` y lo ignorara— devolvería la fila ajena igual, y el test de la barrera
pasaría con la barrera borrada. Es el caso #1 de la doctrina del repo. Por eso `_match` exige
que coincidan TODOS los pares acumulados.

**2. La escritura se arma A PARTIR del payload recibido.** `insert` no devuelve un objeto
prefabricado: construye la fila con lo que le llegó (más `id`/`created_at`). Si el repo deja de
mandar un campo, la fila no lo tiene y el schema no valida. Un doble que devolviera una
constante del test estaría afirmando algo sobre su propia constante.

**3. `escrituras` registra (tabla, filtros, payload) de cada UPDATE y de cada DELETE.** Sin eso no se puede
distinguir "no devolvió nada" de "no escribió nada": un repo que hiciera el UPDATE sin el
`.eq("empresa_id")` y recién filtrara en la relectura devolvería `None` igual, habiendo pisado
la fila ajena.
"""
from typing import Any, Dict, List, Optional
from uuid import uuid4


class Resp:
    def __init__(self, data) -> None:
        self.data = data


class _Q:
    def __init__(self, almacen: "Almacen", tabla: str) -> None:
        self._a, self._tabla = almacen, tabla
        self._filtros: List[tuple] = []
        self._single = False
        self._orden: Optional[str] = None
        self._modo = "select"
        self._payload: Optional[dict] = None
        self._rango: List[tuple] = []
        self._in: Optional[tuple] = None

    def select(self, *a, **k) -> "_Q":
        return self

    def eq(self, col: str, val) -> "_Q":
        """ACUMULA. Quedarse con el último filtro borraría la barrera de empresa."""
        self._filtros.append((col, str(val)))
        return self

    def order(self, col: str, **k) -> "_Q":
        self._orden = col
        return self

    def gte(self, col: str, val) -> "_Q":
        self._rango.append((col, ">=", str(val)))
        return self

    def lte(self, col: str, val) -> "_Q":
        self._rango.append((col, "<=", str(val)))
        return self

    def in_(self, col: str, vals) -> "_Q":
        self._in = (col, [str(v) for v in vals])
        return self

    def delete(self) -> "_Q":
        self._modo = "delete"
        return self

    def maybe_single(self) -> "_Q":
        self._single = True
        return self

    def insert(self, payload: dict) -> "_Q":
        self._modo, self._payload = "insert", payload
        return self

    def update(self, patch: dict) -> "_Q":
        self._modo, self._payload = "update", patch
        return self

    def _match(self, fila: dict) -> bool:
        if not all(str(fila.get(c)) == v for c, v in self._filtros):
            return False
        if self._in and str(fila.get(self._in[0])) not in self._in[1]:
            return False
        # El rango se compara como STRING, que es lo que hace PostgREST con una columna `date`
        # en formato ISO: el orden lexicográfico y el cronológico coinciden.
        for col, op, val in self._rango:
            actual = str(fila.get(col))
            if op == ">=" and actual < val:
                return False
            if op == "<=" and actual > val:
                return False
        return True

    def execute(self) -> Resp:
        filas = self._a.catalogo.setdefault(self._tabla, [])
        if self._modo == "insert":
            nueva = {"id": str(uuid4()), "activo": True, "created_at": self._a.ahora,
                     "updated_at": None, **self._payload}
            filas.append(nueva)
            return Resp([nueva])
        if self._modo == "delete":
            tocadas = [f for f in filas if self._match(f)]
            self._a.escrituras.append((self._tabla, list(self._filtros), "DELETE"))
            for f in tocadas:
                filas.remove(f)
            return Resp(tocadas)
        if self._modo == "update":
            tocadas = [f for f in filas if self._match(f)]
            self._a.escrituras.append((self._tabla, list(self._filtros), dict(self._payload)))
            for f in tocadas:
                f.update(self._payload)
            return Resp(tocadas)
        halladas = [f for f in filas if self._match(f)]
        if self._orden:
            halladas = sorted(halladas, key=lambda f: str(f.get(self._orden, "")))
        if self._single:
            # 🔴 CON 0 FILAS DEVUELVE `None` PELADO, NO `Resp(None)`. Es lo que hace el cliente
            # real (supabase-py 2.9.1) y es la diferencia que este doble NO modelaba, así que
            # ningún test podía desmentirla. El código que escribe `res.data` sin chequear
            # `res` primero pasaba en verde acá y devolvía **500** en producción — medido el
            # 23/8/2026 sobre `POST /api/offboarding`, que fallaba SIEMPRE porque su guarda
            # "¿ya tiene un offboarding activo?" consulta justo el caso de 0 filas.
            # La forma correcta en el repo es `res.data if res and res.data else None`.
            return Resp(halladas[0]) if halladas else None
        return Resp(halladas)


class Almacen:
    """`catalogo` es {tabla: [filas]}. `escrituras` acumula (tabla, filtros, payload) por UPDATE."""

    def __init__(self, catalogo: Dict[str, List[dict]], ahora: str = "2026-08-09T00:00:00+00:00") -> None:
        self.catalogo = catalogo
        self.ahora = ahora
        self.escrituras: List[Any] = []

    def table(self, tabla: str) -> _Q:
        return _Q(self, tabla)
