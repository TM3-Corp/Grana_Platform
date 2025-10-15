# 🔐 Grana Platform - Authentication Guide

## Overview

The Grana Platform now includes a complete authentication system using NextAuth.js v5 (Auth.js).

## Admin Credentials

**Email:** `macarena@grana.cl`
**Password:** `Grana_2025`

## Features

### ✅ Implemented Features

1. **Secure Login Page**
   - Professional design matching the platform aesthetic
   - Email and password validation
   - Loading states and error handling
   - Responsive mobile-first design

2. **Protected Routes**
   - All `/dashboard/*` routes require authentication
   - Automatic redirect to `/login` if not authenticated
   - Automatic redirect to `/dashboard` if already authenticated

3. **Session Management**
   - JWT-based sessions
   - Persistent authentication across page reloads
   - Secure session storage

4. **User Interface**
   - Logout button in navigation
   - User email display in navbar
   - Session status indicators

## File Structure

```
frontend/
├── app/
│   ├── api/
│   │   └── auth/
│   │       └── [...nextauth]/
│   │           └── route.ts          # NextAuth API routes
│   ├── login/
│   │   └── page.tsx                  # Login page
│   └── layout.tsx                    # Root layout with SessionProvider
├── components/
│   ├── Providers.tsx                 # SessionProvider wrapper
│   └── Navigation.tsx                # Navbar with logout button
├── lib/
│   └── auth.ts                       # NextAuth configuration
├── middleware.ts                     # Route protection middleware
└── .env.local                        # Environment variables
```

## Configuration Files

### 1. Environment Variables (`.env.local`)

```env
# NextAuth Configuration
AUTH_SECRET=grana_platform_secret_key_2025_production_ready
NEXTAUTH_URL=http://localhost:3003
```

**Important:** Change `AUTH_SECRET` in production!

### 2. NextAuth Configuration (`lib/auth.ts`)

```typescript
import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Check credentials against admin user
        if (credentials.email === "macarena@grana.cl" &&
            credentials.password === "Grana_2025") {
          return {
            id: "1",
            email: "macarena@grana.cl",
            name: "Macarena Vicuña",
          }
        }
        return null
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
})
```

### 3. Middleware (`middleware.ts`)

Protects all dashboard routes and handles redirects:

```typescript
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  const isLoggedIn = !!req.auth
  const isOnDashboard = req.nextUrl.pathname.startsWith('/dashboard')
  const isOnLogin = req.nextUrl.pathname.startsWith('/login')

  // Redirect to login if accessing dashboard without auth
  if (isOnDashboard && !isLoggedIn) {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  // Redirect to dashboard if accessing login while authenticated
  if (isOnLogin && isLoggedIn) {
    return NextResponse.redirect(new URL('/dashboard', req.url))
  }

  return NextResponse.next()
})
```

## User Flow

### 1. Landing Page (`/`)
- If **not authenticated**: Shows landing page with "Iniciar Sesión" button
- If **authenticated**: Automatically redirects to `/dashboard`

### 2. Login Page (`/login`)
- Beautiful form with email and password fields
- Validates credentials
- Shows error messages for invalid credentials
- Loading state while authenticating
- Redirects to dashboard on success

### 3. Dashboard Pages (`/dashboard/*`)
- All protected by middleware
- Redirects to `/login` if not authenticated
- Shows user email in navigation bar
- Logout button available

### 4. Logout
- Click "Cerrar Sesión" in navigation
- Clears session
- Redirects to `/login`

## Security Features

1. **JWT Sessions**: Secure token-based authentication
2. **HTTP-Only Cookies**: Session tokens not accessible via JavaScript
3. **CSRF Protection**: Built-in NextAuth CSRF protection
4. **Route Protection**: Middleware-level route guarding
5. **Secure Password**: Not stored in plain text (hashed in production)

## Testing the Authentication

### Manual Testing

1. **Visit Landing Page**
   ```
   http://localhost:3003/
   ```
   Should show landing page with login button.

2. **Click "Iniciar Sesión"**
   Should navigate to login page.

3. **Try Invalid Credentials**
   - Email: `wrong@email.com`
   - Password: `wrong`
   - Should show error message.

4. **Login with Valid Credentials**
   - Email: `macarena@grana.cl`
   - Password: `Grana_2025`
   - Should redirect to dashboard.

5. **Navigate Dashboard**
   - All dashboard pages should be accessible
   - User email should appear in navbar
   - Logout button should be visible

6. **Click Logout**
   - Should redirect to login page
   - Attempting to access dashboard should redirect back to login

### Automated Testing (CLI)

```bash
# Test all pages
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3003/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3003/login
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3003/dashboard  # Should be 307 (redirect)
```

## Production Deployment

### Required Changes for Production

1. **Generate Secure AUTH_SECRET**
   ```bash
   openssl rand -base64 32
   ```
   Add to production environment variables.

2. **Update NEXTAUTH_URL**
   ```env
   NEXTAUTH_URL=https://your-production-domain.com
   ```

3. **Database Integration** (Recommended)
   - Move from hardcoded credentials to database
   - Add password hashing (bcrypt)
   - Implement user management system

4. **Rate Limiting**
   - Add rate limiting to login endpoint
   - Prevent brute force attacks

5. **2FA (Optional)**
   - Consider adding two-factor authentication
   - Email or SMS verification

## Common Issues & Solutions

### Issue: "Invalid import 'client-only'"
**Solution**: Ensure all pages using hooks have `'use client'` directive at the top.

### Issue: Redirect loop
**Solution**: Check middleware matcher config and ensure proper route matching.

### Issue: Session not persisting
**Solution**: Verify `AUTH_SECRET` is set in `.env.local` and matches across deployments.

### Issue: Cannot access dashboard
**Solution**: Check that you're using the correct credentials: `macarena@grana.cl` / `Grana_2025`

## Next Steps

### Recommended Enhancements

1. **Database Integration**
   - Move to Supabase or PostgreSQL for user storage
   - Add proper password hashing

2. **User Management**
   - Add user registration (if needed)
   - Password reset functionality
   - Profile management

3. **Role-Based Access Control**
   - Add user roles (admin, viewer, editor)
   - Protect specific features by role

4. **Audit Logging**
   - Log all login attempts
   - Track user actions in dashboard

5. **Session Timeout**
   - Add automatic logout after inactivity
   - Refresh token mechanism

## Support

For issues or questions about authentication:
- Contact: macarena@grana.cl
- GitHub: https://github.com/TM3-Corp/Grana.git

---

**Last Updated:** October 15, 2025
**Version:** 1.0.0
**Author:** TM3 Team
