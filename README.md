# 🍃 Sistema Grana - Integración y Visualización de Datos

Sistema completo de integración de canales de venta y visualización para Grana SpA.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│           FUENTES DE DATOS (APIs)               │
│  Shopify | MercadoLibre | Walmart | Cencosud   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         BACKEND (FastAPI - Railway)             │
│  • Connectors para cada API                     │
│  • Sistema de auditoría completo                │
│  • Endpoints REST para frontend                 │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│      DATABASE (PostgreSQL - Supabase)           │
│  • Single Source of Truth ⭐                    │
│  • Editable y auditable                         │
│  • Audit logging automático                     │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         FRONTEND (Next.js - Vercel)             │
│  • Dashboard de visualización                   │
│  • Editor de pedidos                            │
│  • Análisis de ventas                           │
│  • Alertas de inventario                        │
└─────────────────────────────────────────────────┘
```

## 📁 Estructura del Proyecto

```
grana-system/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── models/      # Modelos de datos
│   │   ├── services/    # Lógica de negocio
│   │   ├── connectors/  # Integraciones con APIs externas
│   │   └── core/        # Configuración y utilidades
│   ├── requirements.txt
│   └── railway.json
│
├── frontend/             # Next.js frontend
│   ├── pages/
│   ├── components/
│   ├── services/
│   └── package.json
│
├── docs/                 # Documentación
│   ├── setup/           # Guías de instalación
│   ├── api/             # Documentación de APIs
│   └── architecture/    # Diagramas y decisiones
│
└── scripts/             # Scripts de utilidad
    ├── migration/       # Migración de datos
    └── sync/            # Sincronización manual
```

## 🚀 Stack Tecnológico

- **Base de Datos**: PostgreSQL en Supabase
- **Backend**: FastAPI (Python) en Railway
- **Frontend**: Next.js (React) en Vercel
- **Auth**: Supabase Auth
- **Storage**: Supabase Storage

## 💰 Costos

- **Mes 1-6**: $0/mes (planes gratuitos)
- **Mes 7+**: ~$45/mes cuando crezca
  - Supabase Pro: $25/mes
  - Railway Pro: $20/mes
  - Vercel: Gratis (hobby plan)

## 📚 Documentación

Ver carpeta `docs/` para:
- [Setup completo](docs/setup/README.md)
- [Documentación de API](docs/api/README.md)
- [Guía de desarrollo](docs/development/README.md)

## 🎯 Próximos Pasos

1. [Setup de Supabase](docs/setup/01-supabase.md)
2. [Setup de Railway](docs/setup/02-railway.md)
3. [Desarrollo del backend](docs/development/backend.md)
4. [Desarrollo del frontend](docs/development/frontend.md)

## 📞 Contacto

- Proyecto: Grana Integration System
- Desarrollado por: TM3
- Cliente: Macarena Vicuña - Grana SpA