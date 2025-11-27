'use client'

import { SessionProvider } from 'next-auth/react'
import FloatingChatWidget from '@/components/FloatingChatWidget'

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider
      // Reduce unnecessary session fetches to prevent "Failed to fetch" errors
      refetchOnWindowFocus={false}
      refetchInterval={0}
    >
      {children}
      <FloatingChatWidget />
    </SessionProvider>
  )
}
