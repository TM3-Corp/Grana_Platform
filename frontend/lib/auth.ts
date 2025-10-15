import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import bcrypt from "bcryptjs"

// Admin credentials - In production, this should be in a database
const ADMIN_USER = {
  email: "macarena@grana.cl",
  name: "Macarena Vicuña",
  // Password: Grana_2025 (hashed)
  passwordHash: "$2a$10$YourHashedPasswordHere" // We'll generate this
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

        // Check if email matches
        if (credentials.email !== ADMIN_USER.email) {
          return null
        }

        // For initial setup, accept the plain password
        // In production, use bcrypt.compare(credentials.password, ADMIN_USER.passwordHash)
        if (credentials.password === "Grana_2025") {
          return {
            id: "1",
            email: ADMIN_USER.email,
            name: ADMIN_USER.name,
          }
        }

        return null
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
      }
      return session
    },
  },
  session: {
    strategy: "jwt",
  },
})
