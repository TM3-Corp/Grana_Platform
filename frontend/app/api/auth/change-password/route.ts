import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { SignJWT } from 'jose';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const AUTH_SECRET = process.env.AUTH_SECRET;

async function getAuthHeaders() {
  const session = await auth();

  if (!session?.user) {
    return null;
  }

  const secret = new TextEncoder().encode(AUTH_SECRET!);
  const backendToken = await new SignJWT({
    id: session.user.id,
    email: session.user.email,
    name: session.user.name,
    role: (session.user as { role?: string }).role,
    sub: session.user.id,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('1h')
    .sign(secret);

  return {
    'Authorization': `Bearer ${backendToken}`,
    'Content-Type': 'application/json',
  };
}

async function safeJsonParse(response: Response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// POST /api/auth/change-password - Change current user's password
export async function POST(request: NextRequest) {
  const headers = await getAuthHeaders();

  if (!headers) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
  }

  try {
    const body = await request.json();

    const response = await fetch(`${API_URL}/api/v1/auth/me/change-password`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await safeJsonParse(response);
    return NextResponse.json(data || { success: true }, { status: response.status });
  } catch (error) {
    console.error('Error changing password:', error);
    return NextResponse.json({ detail: 'Failed to change password' }, { status: 500 });
  }
}
