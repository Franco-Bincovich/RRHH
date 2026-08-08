-- 096_objetivo_responsables.sql
--
-- Múltiples responsables por objetivo: tabla puente `objetivo_responsables`.
--
-- 🔴 `objetivos.responsable_id` SE CONSERVA y NO se toca. La puente SE SUMA, no reemplaza: la
-- columna sigue siendo el DUEÑO PRINCIPAL del objetivo (quien responde por él), y la puente
-- dice quiénes más trabajan en él. Por eso esta migración es enteramente ADITIVA y no hay
-- ningún DROP en ninguna parte — ni acá ni en una migración posterior.
--
-- QUÉ SE GANA CON ESA DECISIÓN, en concreto: `responsable_id` es NOT NULL y tiene índice
-- propio, así que "el dueño" nunca puede quedar sin definir y el orden/filtro por dueño sigue
-- siendo una sola query. Si la columna se hubiera reemplazado, un objetivo podría quedarse sin
-- ningún responsable (una puente vacía es un estado válido) y no habría a quién reclamarle.
--
-- 🔴 PK COMPUESTA (objetivo_id, user_id) Y NO UN `id` PROPIO: la fila NO tiene identidad, ES la
-- relación. Con un `id` surrogate haría falta además un UNIQUE sobre el par para impedir que el
-- mismo usuario se cargue dos veces en el mismo objetivo — o sea, el mismo índice más una
-- columna que nadie mira. La PK compuesta hace que el duplicado sea imposible por construcción
-- y da el índice de `objetivo_id` gratis (es el prefijo de la PK).
--
-- Las dos FKs van con ON DELETE CASCADE, por motivos distintos:
--   · objetivo_id → si el objetivo se borra, sus filas de responsables no significan nada. Y se
--     compone con el cascade de `parent_id` (migración 095): borrar un padre se lleva a los
--     hijos, y a los responsables de los hijos.
--   · user_id → un usuario dado de baja no debe dejar filas apuntando a un id que ya no
--     resuelve a ningún nombre. ⚠️ Ojo: la baja de usuario del repo es BLANDA (`activo=false`,
--     ver `usuario_service.eliminar_usuario`), así que este cascade en la práctica casi nunca
--     dispara. Está por corrección, no porque se espere que corra.
--
-- BACKFILL: cada objetivo existente pasa a tener a su `responsable_id` también en la puente.
-- Sin esto, el listado filtrado por responsable —que después de esta migración busca por la
-- puente— dejaría de encontrar los objetivos que ya existen. Es idempotente por la PK: si el
-- script se corre dos veces, el ON CONFLICT DO NOTHING no duplica nada.

CREATE TABLE IF NOT EXISTS public.objetivo_responsables (
    objetivo_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT objetivo_responsables_pkey PRIMARY KEY (objetivo_id, user_id),
    CONSTRAINT objetivo_responsables_objetivo_id_fkey
        FOREIGN KEY (objetivo_id) REFERENCES public.objetivos(id) ON DELETE CASCADE,
    CONSTRAINT objetivo_responsables_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- La PK ya indexa (objetivo_id, user_id) y sirve para "los responsables de este objetivo".
-- Este índice cubre la pregunta INVERSA —"los objetivos de este usuario"—, que es la que hace
-- el filtro por responsable del listado y que la PK NO puede responder: user_id es la segunda
-- columna del índice compuesto, no su prefijo.
CREATE INDEX IF NOT EXISTS idx_obj_resp_user
    ON public.objetivo_responsables USING btree (user_id);

INSERT INTO public.objetivo_responsables (objetivo_id, user_id)
SELECT id, responsable_id FROM public.objetivos
ON CONFLICT (objetivo_id, user_id) DO NOTHING;
