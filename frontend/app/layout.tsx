import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { ThemeProvider } from "@/components/layout/ThemeProvider"
import { Toaster } from "@/components/ui/sonner"
import "./globals.css"
import { MARCA } from "@/lib/marca"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
})

export const metadata: Metadata = {
  title: MARCA,
  description: "Plataforma de gestión del ciclo de vida del colaborador",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="es"
      className={inter.variable}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background antialiased">
        <ThemeProvider>
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
