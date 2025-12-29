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

// GET /api/users - List all users
export async function GET() {
  const headers = await getAuthHeaders();

  if (!headers) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/auth/users`, {
      headers,
    });

    const data = await safeJsonParse(response);
    return NextResponse.json(data || [], { status: response.status });
  } catch (error) {
    console.error('Error fetching users:', error);
    return NextResponse.json({ detail: 'Failed to fetch users' }, { status: 500 });
  }
}

// POST /api/users - Create a new user
export async function POST(request: NextRequest) {
  const headers = await getAuthHeaders();

  if (!headers) {
    return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
  }

  try {
    const body = await request.json();

    const response = await fetch(`${API_URL}/api/v1/auth/users`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await safeJsonParse(response);
    return NextResponse.json(data || { success: true }, { status: response.status });
  } catch (error) {
    console.error('Error creating user:', error);
    return NextResponse.json({ detail: 'Failed to create user' }, { status: 500 });
  }
}
