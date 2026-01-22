'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useState, useEffect, useRef } from 'react';
import { signOut, useSession } from 'next-auth/react';
import {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  Table2,
  Package,
  Boxes,
  Warehouse,
  Factory,
  Tags,
  BookOpen,
  Link2,
  ArrowLeftRight,
  ChevronDown,
  User,
  Users,
  LogOut,
  Menu,
  X,
  type LucideIcon
} from 'lucide-react';

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

  // Navigation structure with Lucide icons
  interface NavItem {
    name: string;
    href?: string;
    icon: LucideIcon;
    isDropdown?: boolean;
    subItems?: { name: string; href: string; icon: LucideIcon }[];
  }

  // Color themes for each section
  const sectionColors: Record<string, { active: string; hover: string; icon: string }> = {
    'Dashboard': { active: 'from-emerald-500 to-green-600', hover: 'hover:bg-emerald-50', icon: 'text-emerald-600' },
    'Ventas': { active: 'from-blue-500 to-indigo-600', hover: 'hover:bg-blue-50', icon: 'text-blue-600' },
    'Inventario': { active: 'from-amber-500 to-orange-600', hover: 'hover:bg-amber-50', icon: 'text-amber-600' },
    'Productos': { active: 'from-purple-500 to-violet-600', hover: 'hover:bg-purple-50', icon: 'text-purple-600' },
  };

  const navigation: NavItem[] = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    {
      name: 'Ventas',
      icon: TrendingUp,
      isDropdown: true,
      subItems: [
        { name: 'Visualizaciones', href: '/dashboard/sales-analytics', icon: BarChart3 },
        { name: 'Tablas', href: '/dashboard/orders', icon: Table2 },
      ]
    },
    {
      name: 'Inventario',
      icon: Package,
      isDropdown: true,
      subItems: [
        { name: 'General', href: '/dashboard/warehouse-inventory', icon: Boxes },
        { name: 'Por Bodega', href: '/dashboard/warehouse-inventory/by-warehouse', icon: Warehouse },
        { name: 'Planificación', href: '/dashboard/production-planning', icon: Factory },
      ]
    },
    {
      name: 'Productos',
      icon: Tags,
      isDropdown: true,
      subItems: [
        { name: 'Catálogo', href: '/dashboard/product-catalog', icon: BookOpen },
        { name: 'Mapeo SKUs', href: '/dashboard/sku-mappings', icon: Link2 },
        { name: 'Mapeo Canales', href: '/dashboard/channel-mappings', icon: ArrowLeftRight },
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
          <div className="flex items-center ml-14">
            <Link href="/" className="flex items-center hover:opacity-80 transition-opacity">
              <Image
                src="/images/logo_grana.avif"
                alt="Grana"
                width={80}
                height={80}
                className="object-contain"
                style={{ height: 'auto' }}
              />
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {navigation.map((item) => {
              const IconComponent = item.icon;

              if (item.isDropdown && item.subItems) {
                // Dropdown menu for Ventas and Inventario
                const isDropActive = isDropdownActive(item.subItems);
                const colors = sectionColors[item.name];
                return (
                  <div
                    key={item.name}
                    className="relative"
                    onMouseEnter={() => setOpenDropdown(item.name)}
                    onMouseLeave={() => setOpenDropdown(null)}
                  >
                    <button
                      className={`
                        px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                        flex items-center gap-2
                        ${
                          isDropActive
                            ? `bg-gradient-to-r ${colors.active} text-white shadow-sm`
                            : `text-gray-700 ${colors.hover} hover:text-gray-900`
                        }
                      `}
                    >
                      <IconComponent className={`w-4 h-4 ${!isDropActive ? colors.icon : ''}`} strokeWidth={1.75} />
                      <span>{item.name}</span>
                      <ChevronDown
                        className={`w-4 h-4 transition-transform duration-200 ${openDropdown === item.name ? 'rotate-180' : ''}`}
                        strokeWidth={1.75}
                      />
                    </button>

                    {/* Dropdown menu */}
                    {openDropdown === item.name && (
                      <div className="absolute left-0 top-full w-48 pt-1 z-50">
                        <div className="bg-white rounded-xl shadow-lg border border-gray-200 py-2">
                        {item.subItems.map((subItem) => {
                          const SubIconComponent = subItem.icon;
                          const isItemActive = isActive(subItem.href);
                          return (
                            <Link
                              key={subItem.href}
                              href={subItem.href}
                              className={`
                                block px-4 py-2.5 text-sm transition-all duration-200
                                flex items-center gap-3 mx-2 rounded-lg
                                ${
                                  isItemActive
                                    ? `bg-gradient-to-r ${colors.active} text-white shadow-sm`
                                    : `text-gray-700 ${colors.hover}`
                                }
                              `}
                            >
                              <SubIconComponent className={`w-4 h-4 ${!isItemActive ? colors.icon : ''}`} strokeWidth={1.75} />
                              <span>{subItem.name}</span>
                            </Link>
                          );
                        })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }

              // Regular navigation item
              const colors = sectionColors[item.name];
              const isItemActive = isActive(item.href!);
              return (
                <Link
                  key={item.href}
                  href={item.href!}
                  className={`
                    px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                    flex items-center gap-2
                    ${
                      isItemActive
                        ? `bg-gradient-to-r ${colors.active} text-white shadow-sm`
                        : `text-gray-700 ${colors.hover} hover:text-gray-900`
                    }
                  `}
                >
                  <IconComponent className={`w-4 h-4 ${!isItemActive ? colors.icon : ''}`} strokeWidth={1.75} />
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
                  className="flex items-center gap-2 hover:bg-gray-50 rounded-lg px-2 py-1.5 transition-all duration-200"
                >
                  {/* Avatar with initials */}
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center text-white text-sm font-medium shadow-sm">
                    {getInitials(session.user?.name || session.user?.email)}
                  </div>
                  <span className="text-sm text-gray-700 hidden lg:block max-w-32 truncate">
                    {session.user?.name || session.user?.email}
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${userMenuOpen ? 'rotate-180' : ''}`}
                    strokeWidth={1.75}
                  />
                </button>

                {/* Dropdown Menu */}
                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-lg border border-gray-200 py-2 z-50">
                    {/* User Info Header */}
                    <div className="px-4 py-3 border-b border-gray-100 mx-2 rounded-lg bg-gradient-to-r from-gray-50 to-slate-50">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {session.user?.name || 'Usuario'}
                      </p>
                      <p className="text-xs text-gray-500 truncate">{session.user?.email}</p>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2 px-2">
                      <Link
                        href="/dashboard/profile"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 hover:bg-emerald-50 hover:text-emerald-700 rounded-lg transition-all duration-200"
                      >
                        <User className="w-4 h-4 text-emerald-500" strokeWidth={1.75} />
                        Perfil
                      </Link>

                      {/* Admin Only - User Management */}
                      {userRole === 'admin' && (
                        <Link
                          href="/dashboard/users"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 rounded-lg transition-all duration-200"
                        >
                          <Users className="w-4 h-4 text-blue-500" strokeWidth={1.75} />
                          Gestión de Usuarios
                        </Link>
                      )}
                    </div>

                    {/* Divider */}
                    <div className="border-t border-gray-100 my-1 mx-2"></div>

                    {/* Logout */}
                    <div className="py-1 px-2">
                      <button
                        onClick={() => {
                          setUserMenuOpen(false);
                          const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
                          signOut({ callbackUrl: `${baseUrl}/login` });
                        }}
                        className="flex items-center gap-3 px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 w-full rounded-lg transition-all duration-200"
                      >
                        <LogOut className="w-4 h-4" strokeWidth={1.75} />
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
                <X className="h-6 w-6" strokeWidth={1.5} />
              ) : (
                <Menu className="h-6 w-6" strokeWidth={1.5} />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navigation.map((item) => {
              const IconComponent = item.icon;

              if (item.isDropdown && item.subItems) {
                // Dropdown items for mobile - show as expandable list
                const colors = sectionColors[item.name];
                return (
                  <div key={item.name}>
                    <div className="px-3 py-2 text-sm font-semibold text-gray-500 flex items-center gap-2">
                      <IconComponent className={`w-4 h-4 ${colors.icon}`} strokeWidth={1.75} />
                      <span>{item.name}</span>
                    </div>
                    {item.subItems.map((subItem) => {
                      const SubIconComponent = subItem.icon;
                      const isItemActive = isActive(subItem.href);
                      return (
                        <Link
                          key={subItem.href}
                          href={subItem.href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={`
                            block px-6 py-2.5 rounded-lg text-base font-medium mx-2 mb-1
                            flex items-center gap-2 transition-all duration-200
                            ${
                              isItemActive
                                ? `bg-gradient-to-r ${colors.active} text-white shadow-sm`
                                : `text-gray-700 ${colors.hover}`
                            }
                          `}
                        >
                          <SubIconComponent className={`w-4 h-4 ${!isItemActive ? colors.icon : ''}`} strokeWidth={1.75} />
                          <span>{subItem.name}</span>
                        </Link>
                      );
                    })}
                  </div>
                );
              }

              // Regular navigation item
              const colors = sectionColors[item.name];
              const isItemActive = isActive(item.href!);
              return (
                <Link
                  key={item.href}
                  href={item.href!}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`
                    block px-3 py-2.5 rounded-lg text-base font-medium mx-2 mb-1
                    flex items-center gap-2 transition-all duration-200
                    ${
                      isItemActive
                        ? `bg-gradient-to-r ${colors.active} text-white shadow-sm`
                        : `text-gray-700 ${colors.hover}`
                    }
                  `}
                >
                  <IconComponent className={`w-4 h-4 ${!isItemActive ? colors.icon : ''}`} strokeWidth={1.75} />
                  <span>{item.name}</span>
                </Link>
              );
            })}

            {/* Mobile User Section */}
            {session && (
              <>
                <div className="border-t border-gray-200 my-3 mx-2"></div>
                <div className="px-3 py-2 text-sm font-semibold text-gray-500 flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center text-white text-xs font-medium shadow-sm">
                    {getInitials(session.user?.name || session.user?.email)}
                  </div>
                  <span className="truncate">{session.user?.name || session.user?.email}</span>
                </div>
                <Link
                  href="/dashboard/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`
                    block px-6 py-2.5 rounded-lg text-base font-medium mx-2 mb-1
                    flex items-center gap-2 transition-all duration-200
                    ${
                      isActive('/dashboard/profile')
                        ? 'bg-gradient-to-r from-emerald-500 to-green-600 text-white shadow-sm'
                        : 'text-gray-700 hover:bg-emerald-50'
                    }
                  `}
                >
                  <User className={`w-4 h-4 ${!isActive('/dashboard/profile') ? 'text-emerald-500' : ''}`} strokeWidth={1.75} />
                  <span>Perfil</span>
                </Link>
                {userRole === 'admin' && (
                  <Link
                    href="/dashboard/users"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`
                      block px-6 py-2.5 rounded-lg text-base font-medium mx-2 mb-1
                      flex items-center gap-2 transition-all duration-200
                      ${
                        isActive('/dashboard/users')
                          ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-sm'
                          : 'text-gray-700 hover:bg-blue-50'
                      }
                    `}
                  >
                    <Users className={`w-4 h-4 ${!isActive('/dashboard/users') ? 'text-blue-500' : ''}`} strokeWidth={1.75} />
                    <span>Gestión de Usuarios</span>
                  </Link>
                )}
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
                    signOut({ callbackUrl: `${baseUrl}/login` });
                  }}
                  className="block w-full text-left px-6 py-2.5 rounded-lg text-base font-medium text-red-600 hover:bg-red-50 flex items-center gap-2 mx-2 transition-all duration-200"
                >
                  <LogOut className="w-4 h-4" strokeWidth={1.75} />
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
