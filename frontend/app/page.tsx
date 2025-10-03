import Link from "next/link";

export default function Home() {
  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-8 row-start-2 items-center">
        <h1 className="text-4xl font-bold text-center">
          🍃 Grana Platform
        </h1>
        <p className="text-center text-gray-600 max-w-md">
          Sistema de integración y visualización de datos de ventas para Grana SpA
        </p>

        <div className="flex gap-4 items-center flex-col sm:flex-row mt-8">
          <Link
            href="/dashboard"
            className="rounded-full border border-solid border-transparent transition-colors flex items-center justify-center bg-green-600 text-white gap-2 hover:bg-green-700 font-medium text-sm sm:text-base h-12 px-6"
          >
            📊 Ver Dashboard
          </Link>
          <a
            href={process.env.NEXT_PUBLIC_API_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-solid border-gray-300 transition-colors flex items-center justify-center hover:bg-gray-100 font-medium text-sm sm:text-base h-12 px-6"
          >
            🔌 API Backend
          </a>
        </div>

        <div className="mt-12 bg-gray-50 rounded-lg p-6 max-w-2xl">
          <h2 className="font-semibold mb-3">Estado del Sistema:</h2>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span>
              <span>Frontend en Vercel (Next.js)</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span>
              <span>Backend en Railway (FastAPI)</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span>
              <span>Base de datos en Supabase (PostgreSQL)</span>
            </li>
          </ul>
        </div>
      </main>
      <footer className="row-start-3 text-center text-sm text-gray-500">
        Desarrollado para Grana SpA - TM3 Corp
      </footer>
    </div>
  );
}
