'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useState, useEffect, useRef } from 'react';
import { signOut, useSession } from 'next-auth/react';

// Helper function to get initials from name or email
function getInitials(nameOrEmail: string | null | undefined): string {
  if (!nameOrEmail) return '?';
  const parts = nameOrEmail.split(/[@\s]+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return nameOrEmail.substring(0, 2).toUpperCase();
}

export default function Navigation() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const { data: session } = useSession();

  // Close user menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const userRole = (session?.user as { role?: string })?.role;

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: '📊' },
    {
      name: 'Ventas',
      icon: '📈',
      isDropdown: true,
      subItems: [
        { name: 'Visualizaciones', href: '/dashboard/sales-analytics', icon: '🎯' },
        { name: 'Tablas', href: '/dashboard/orders', icon: '📋' },
      ]
    },
    {
      name: 'Inventario',
      icon: '📦',
      isDropdown: true,
      subItems: [
        { name: 'General', href: '/dashboard/warehouse-inventory', icon: '📦' },
        { name: 'Por Bodega', href: '/dashboard/warehouse-inventory/by-warehouse', icon: '🏢' },
        { name: 'Planificación', href: '/dashboard/production-planning', icon: '🏭' },
      ]
    },
    {
      name: 'Productos',
      icon: '🏷️',
      isDropdown: true,
      subItems: [
        { name: 'Catálogo', href: '/dashboard/product-catalog', icon: '📋' },
        { name: 'Mapeo SKUs', href: '/dashboard/sku-mappings', icon: '🔗' },
      ]
    },
  ];

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === href;
    }
    return pathname?.startsWith(href);
  };

  const isDropdownActive = (subItems: any[]) => {
    return subItems.some(item => pathname?.startsWith(item.href));
  };

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center hover:opacity-80 transition-opacity">
              <Image
                src="/images/logo_grana.avif"
                alt="Grana"
                width={40}
                height={40}
                className="object-contain"
                style={{ height: 'auto' }}
              />
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {navigation.map((item: any) => {
              if (item.isDropdown) {
                // Dropdown menu for Ventas and Inventario
                const isDropActive = isDropdownActive(item.subItems);
                return (
                  <div
                    key={item.name}
                    className="relative"
                    onMouseEnter={() => setOpenDropdown(item.name)}
                    onMouseLeave={() => setOpenDropdown(null)}
                  >
                    <button
                      className={`
                        px-4 py-2 rounded-lg text-sm font-medium transition-all
                        flex items-center gap-2
                        ${
                          isDropActive
                            ? 'bg-green-50 text-green-700'
                            : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                        }
                      `}
                    >
                      <span>{item.icon}</span>
                      <span>{item.name}</span>
                      <svg
                        className={`w-4 h-4 transition-transform ${openDropdown === item.name ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {/* Dropdown menu */}
                    {openDropdown === item.name && (
                      <div className="absolute left-0 top-full w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                        {item.subItems.map((subItem: any) => (
                          <Link
                            key={subItem.href}
                            href={subItem.href}
                            className={`
                              block px-4 py-2 text-sm transition-colors
                              flex items-center gap-2
                              ${
                                isActive(subItem.href)
                                  ? 'bg-green-50 text-green-700'
                                  : 'text-gray-700 hover:bg-gray-50'
                              }
                            `}
                          >
                            <span>{subItem.icon}</span>
                            <span>{subItem.name}</span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                );
              }

              // Regular navigation item
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    px-4 py-2 rounded-lg text-sm font-medium transition-all
                    flex items-center gap-2
                    ${
                      isActive(item.href)
                        ? 'bg-green-50 text-green-700'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                >
                  <span>{item.icon}</span>
                  <span>{item.name}</span>
                </Link>
              );
            })}

            {/* User Menu Dropdown */}
            {session && (
              <div
                ref={userMenuRef}
                className="relative ml-4 pl-4 border-l border-gray-200"
              >
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 hover:bg-gray-50 rounded-lg px-2 py-1 transition-all"
                >
                  {/* Avatar with initials */}
                  <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-white text-sm font-medium">
                    {getInitials(session.user?.name || session.user?.email)}
                  </div>
                  <span className="text-sm text-gray-700 hidden lg:block max-w-32 truncate">
                    {session.user?.name || session.user?.email}
                  </span>
                  <svg
                    className={`w-4 h-4 text-gray-500 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                    {/* User Info Header */}
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {session.user?.name || 'Usuario'}
                      </p>
                      <p className="text-xs text-gray-500 truncate">{session.user?.email}</p>
                    </div>

                    {/* Menu Items */}
                    <div className="py-1">
                      <Link
                        href="/dashboard/profile"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        Perfil
                      </Link>

                      {/* Admin Only - User Management */}
                      {userRole === 'admin' && (
                        <Link
                          href="/dashboard/users"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                          </svg>
                          Gestión de Usuarios
                        </Link>
                      )}
                    </div>

                    {/* Divider */}
                    <div className="border-t border-gray-100 my-1"></div>

                    {/* Logout */}
                    <div className="py-1">
                      <button
                        onClick={() => {
                          setUserMenuOpen(false);
                          const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
                          signOut({ callbackUrl: `${baseUrl}/login` });
                        }}
                        className="flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        Cerrar Sesión
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-green-500"
            >
              <span className="sr-only">Abrir menú</span>
              {mobileMenuOpen ? (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navigation.map((item: any) => {
              if (item.isDropdown) {
                // Dropdown items for mobile - show as expandable list
                return (
                  <div key={item.name}>
                    <div className="px-3 py-2 text-sm font-semibold text-gray-500 flex items-center gap-2">
                      <span>{item.icon}</span>
                      <span>{item.name}</span>
                    </div>
                    {item.subItems.map((subItem: any) => (
                      <Link
                        key={subItem.href}
                        href={subItem.href}
                        onClick={() => setMobileMenuOpen(false)}
                        className={`
                          block px-6 py-2 rounded-md text-base font-medium
                          flex items-center gap-2
                          ${
                            isActive(subItem.href)
                              ? 'bg-green-50 text-green-700'
                              : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                          }
                        `}
                      >
                        <span>{subItem.icon}</span>
                        <span>{subItem.name}</span>
                      </Link>
                    ))}
                  </div>
                );
              }

              // Regular navigation item
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`
                    block px-3 py-2 rounded-md text-base font-medium
                    flex items-center gap-2
                    ${
                      isActive(item.href)
                        ? 'bg-green-50 text-green-700'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                >
                  <span>{item.icon}</span>
                  <span>{item.name}</span>
                </Link>
              );
            })}

            {/* Mobile User Section */}
            {session && (
              <>
                <div className="border-t border-gray-200 my-2"></div>
                <div className="px-3 py-2 text-sm font-semibold text-gray-500 flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-green-600 flex items-center justify-center text-white text-xs font-medium">
                    {getInitials(session.user?.name || session.user?.email)}
                  </div>
                  <span className="truncate">{session.user?.name || session.user?.email}</span>
                </div>
                <Link
                  href="/dashboard/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`
                    block px-6 py-2 rounded-md text-base font-medium
                    flex items-center gap-2
                    ${
                      isActive('/dashboard/profile')
                        ? 'bg-green-50 text-green-700'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>Perfil</span>
                </Link>
                {userRole === 'admin' && (
                  <Link
                    href="/dashboard/users"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`
                      block px-6 py-2 rounded-md text-base font-medium
                      flex items-center gap-2
                      ${
                        isActive('/dashboard/users')
                          ? 'bg-green-50 text-green-700'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                      }
                    `}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <span>Gestión de Usuarios</span>
                  </Link>
                )}
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
                    signOut({ callbackUrl: `${baseUrl}/login` });
                  }}
                  className="block w-full text-left px-6 py-2 rounded-md text-base font-medium text-red-600 hover:bg-red-50 flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>Cerrar Sesión</span>
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
