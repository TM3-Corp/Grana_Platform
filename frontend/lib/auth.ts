import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import bcrypt from "bcryptjs"

// Supabase connection for user authentication
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

async function getUserFromDatabase(email: string) {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.error('Supabase credentials not configured')
    return null
  }

  try {
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/users?email=eq.${encodeURIComponent(email)}&is_active=eq.true&select=id,email,password_hash,name,role`,
      {
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        },
      }
    )

    if (!response.ok) {
      console.error('Failed to fetch user:', response.statusText)
      return null
    }

    const users = await response.json()
    return users[0] || null
  } catch (error) {
    console.error('Error fetching user:', error)
    return null
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }

        // Fetch user from database
        const user = await getUserFromDatabase(credentials.email as string)

        if (!user) {
          console.log('User not found:', credentials.email)
          return null
        }

        // Verify password with bcrypt
        const isValidPassword = await bcrypt.compare(
          credentials.password as string,
          user.password_hash
        )

        if (!isValidPassword) {
          console.log('Invalid password for:', credentials.email)
          return null
        }

        // Return user data for session
        return {
          id: user.id.toString(),
          email: user.email,
          name: user.name,
          role: user.role,
        }
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user
      const isOnDashboard = nextUrl.pathname.startsWith('/dashboard')

      // Require authentication for dashboard routes
      if (isOnDashboard) {
        return isLoggedIn
      }

      return true
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.role = (user as { role?: string }).role
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
        ;(session.user as { role?: string }).role = token.role as string
      }
      return session
    },
  },
  session: {
    strategy: "jwt",
  },
  trustHost: true, // Required for NextAuth v5 in development
})
