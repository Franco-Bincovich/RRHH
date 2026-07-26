import { AuthGuard } from "@/components/layout/AuthGuard"
import { Sidebar } from "@/components/layout/Sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-4 pt-16 lg:p-8 lg:pt-8">
          {children}
        </main>
      </div>
    </AuthGuard>
  )
}
