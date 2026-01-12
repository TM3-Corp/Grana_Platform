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

// GET /api/users/[id] - Get a specific user
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const headers = await getAuthHeaders();

  if (!headers) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
  }

  const { id } = await params;

  try {
    const response = await fetch(`${API_URL}/api/v1/auth/users/${id}`, {
      headers,
    });

    const data = await safeJsonParse(response);
    return NextResponse.json(data || { detail: 'No data' }, { status: response.status });
  } catch (error) {
    console.error('Error fetching user:', error);
    return NextResponse.json({ detail: 'Failed to fetch user' }, { status: 500 });
  }
}

// PATCH /api/users/[id] - Update a user
export async function PATCH(
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

    const response = await fetch(`${API_URL}/api/v1/auth/users/${id}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    });

    const data = await safeJsonParse(response);
    return NextResponse.json(data || { success: true }, { status: response.status });
  } catch (error) {
    console.error('Error updating user:', error);
    return NextResponse.json({ detail: 'Failed to update user' }, { status: 500 });
  }
}

// DELETE /api/users/[id] - Delete a user
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const headers = await getAuthHeaders();

  if (!headers) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
  }

  const { id } = await params;

  try {
    const response = await fetch(`${API_URL}/api/v1/auth/users/${id}`, {
      method: 'DELETE',
      headers,
    });

    const data = await safeJsonParse(response);
    return NextResponse.json(data || { success: true }, { status: response.status });
  } catch (error) {
    console.error('Error deleting user:', error);
    return NextResponse.json({ detail: 'Failed to delete user' }, { status: 500 });
  }
}
