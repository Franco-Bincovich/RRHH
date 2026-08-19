import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"

/** Etiqueta + valor de un dato del legajo. Muestra "—" cuando el valor es nulo/vacío. */
export function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-foreground">{value ?? "—"}</dd>
    </div>
  )
}

/** Tarjeta con título y grilla de campos. Contenedor de cada bloque de la ficha. */
export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card as="section">
      <h2 className="mb-4 text-base font-semibold text-foreground">{title}</h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</dl>
    </Card>
  )
}

/** Placeholder de carga de la ficha (header + tres tarjetas). */
export function LoadingSkeleton() {
  return (
    <div>
      <Skeleton className="mb-6 h-8 w-48" />
      <div className="space-y-4">
        <Skeleton className="h-44 w-full rounded-xl" />
        <Skeleton className="h-44 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
    </div>
  )
}
