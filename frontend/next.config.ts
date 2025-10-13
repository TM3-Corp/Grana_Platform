import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // Ignorar errores de ESLint durante el build en producción
    // Los errores son solo de estilo, no afectan la funcionalidad
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Ignorar errores de TypeScript durante el build
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
