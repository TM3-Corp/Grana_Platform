import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  const { nextUrl } = req
  const isLoggedIn = !!req.auth

  const isOnDashboard = nextUrl.pathname.startsWith('/dashboard')
  const isOnLogin = nextUrl.pathname.startsWith('/login')
  const isOnRoot = nextUrl.pathname === '/'

  // Redirect root to dashboard if logged in, otherwise to login
  if (isOnRoot) {
    if (isLoggedIn) {
      return NextResponse.redirect(new URL('/dashboard', nextUrl))
    }
    return NextResponse.redirect(new URL('/login', nextUrl))
  }

  // Protect all dashboard routes - redirect to login if not authenticated
  if (isOnDashboard && !isLoggedIn) {
    const loginUrl = new URL('/login', nextUrl)
    loginUrl.searchParams.set('callbackUrl', nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  // If on login and already logged in, redirect to dashboard
  if (isOnLogin && isLoggedIn) {
    return NextResponse.redirect(new URL('/dashboard', nextUrl))
  }

  return NextResponse.next()
})

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (authentication endpoints)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images (public images)
     */
    '/((?!api/auth|_next/static|_next/image|favicon.ico|images).*)',
  ],
}
