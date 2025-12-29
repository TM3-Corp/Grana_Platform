import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { encode } from 'next-auth/jwt';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const AUTH_SECRET = process.env.AUTH_SECRET;

async function getAuthHeaders() {
  const session = await auth();

  if (!session?.user) {
    return null;
  }

  // Create a JWT token to send to the backend
  const token = await encode({
    token: {
      id: session.user.id,
      email: session.user.email,
      name: session.user.name,
      role: (session.user as { role?: string }).role,
    },
    secret: AUTH_SECRET!,
  });

  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// POST /api/users/[id]/reset-password - Reset a user's password (admin only)
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const headers = await getAuthHeaders();

  if (!headers) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
  }

  const { id } = await params;

  try {
    const body = await request.json();

    const response = await fetch(`${API_URL}/api/v1/auth/users/${id}/reset-password`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error resetting password:', error);
    return NextResponse.json({ detail: 'Failed to reset password' }, { status: 500 });
  }
}
