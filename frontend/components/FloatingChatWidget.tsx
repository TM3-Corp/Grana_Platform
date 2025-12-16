'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { usePathname } from 'next/navigation';

// ============================================================================
// FLOATING CHAT WIDGET
// A global AI assistant that appears on all authenticated pages
// Best practices: Intercom/Zendesk style floating button
// ============================================================================

export default function FloatingChatWidget() {
  const { status } = useSession();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Don't show on login page or if not authenticated
  const shouldHide =
    status !== 'authenticated' ||
    pathname === '/login' ||
    pathname === '/';

  // Handle ESC key to close
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && isOpen) {
      setIsOpen(false);
    }
  }, [isOpen]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Prevent body scroll when chat is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (shouldHide) return null;

  return (
    <>
      {/* Backdrop (mobile always, desktop only when expanded) */}
      {isOpen && (
        <div
          className={`fixed inset-0 bg-black/30 z-40 ${isExpanded ? '' : 'md:hidden'}`}
          onClick={() => {
            setIsOpen(false);
            setIsExpanded(false);
          }}
          aria-hidden="true"
        />
      )}

      {/* Chat Panel */}
      <div
        className={`
          fixed z-50 transition-all duration-300 ease-out
          ${isOpen
            ? 'opacity-100 translate-y-0 pointer-events-auto'
            : 'opacity-0 translate-y-4 pointer-events-none'
          }

          /* Mobile: Full screen */
          bottom-0 left-0 right-0 top-0

          /* Desktop: Normal or Expanded */
          ${isExpanded
            ? 'md:bottom-4 md:right-4 md:left-4 md:top-4'
            : 'md:bottom-24 md:right-6 md:left-auto md:top-auto md:w-[420px] md:h-[600px] md:max-h-[calc(100vh-120px)]'
          }
        `}
      >
        <div className="h-full md:rounded-2xl md:shadow-2xl overflow-hidden bg-white flex flex-col">
          {/* Custom Header for Widget Mode */}
          <div className="px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47-2.47m0 0a3.375 3.375 0 00-4.773 0L9.5 14.5m4.03-2.47l.22-.22a1.5 1.5 0 012.121 0l1.629 1.629m-9 0l-2.47 2.47" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-base">Asistente IA Grana</h3>
                <p className="text-green-100 text-xs">Pregunta sobre inventario, ventas...</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {/* Minimize Button */}
              <button
                onClick={() => setIsOpen(false)}
                className="w-8 h-8 rounded-full hover:bg-white/20 flex items-center justify-center transition-colors"
                aria-label="Minimizar chat"
                title="Minimizar"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Expand/Collapse Button (Desktop only) */}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="hidden md:flex w-8 h-8 rounded-full hover:bg-white/20 items-center justify-center transition-colors"
                aria-label={isExpanded ? "Reducir" : "Expandir"}
                title={isExpanded ? "Reducir" : "Expandir"}
              >
                {isExpanded ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                  </svg>
                )}
              </button>

              {/* Close Button */}
              <button
                onClick={() => {
                  setIsOpen(false);
                  setIsExpanded(false);
                }}
                className="w-8 h-8 rounded-full hover:bg-white/20 flex items-center justify-center transition-colors"
                aria-label="Cerrar chat"
                title="Cerrar"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Chat Content - Reusing existing component */}
          <div className="flex-1 overflow-hidden">
            <InventoryChatPanelEmbedded />
          </div>
        </div>
      </div>

      {/* Floating Button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          setHasInteracted(true);
        }}
        className={`
          fixed bottom-6 right-6 z-50
          w-14 h-14 rounded-full
          bg-gradient-to-r from-green-600 to-emerald-600
          text-white shadow-lg
          flex items-center justify-center
          transition-all duration-300 ease-out
          hover:scale-110 hover:shadow-xl
          active:scale-95
          ${isOpen ? 'rotate-0' : 'rotate-0'}
        `}
        aria-label={isOpen ? 'Cerrar asistente IA' : 'Abrir asistente IA'}
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        )}

        {/* Pulse animation when not interacted */}
        {!hasInteracted && !isOpen && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-green-500"></span>
          </span>
        )}
      </button>
    </>
  );
}

// ============================================================================
// EMBEDDED VERSION OF CHAT PANEL (without header, for widget use)
// ============================================================================

import { useState as useStateEmbed, useRef, useEffect as useEffectEmbed, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dynamic from 'next/dynamic';

// Dynamically import ChatChart to avoid SSR issues with Recharts
const ChatChart = dynamic(() => import('./ChatChart'), { ssr: false });
import { parseChartDataFromMessage, removeChartDataFromMessage } from './ChatChart';

interface ChartDataType {
  chart_type?: string;
  data?: { labels: string[]; datasets: unknown[] };
  historical_data?: unknown;
  forecast?: unknown;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  toolsUsed?: string[];
  chartData?: ChartDataType[];
  usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    context_messages: number;
  };
}

interface ChatResponse {
  success: boolean;
  response: string;
  tools_used: string[];
  model: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    context_messages: number;
  };
  timestamp: string;
}

const QUICK_ACTIONS = [
  { label: 'Resumen', query: 'Dame un resumen del inventario total' },
  { label: 'Por Vencer', query: 'Que productos estan por vencer?' },
  { label: 'Stock Critico', query: 'Que productos tienen stock critico?' },
  { label: 'Top Ventas', query: 'Top 10 productos mas vendidos este mes' },
  { label: '📊 Gráfico', query: 'Muestrame un grafico de barras de ventas por canal en 2025' },
  { label: '📈 Proyección', query: 'Dame la proyeccion de ventas para 2026 basado en 2025' },
];

function InventoryChatPanelEmbedded() {
  const [messages, setMessages] = useStateEmbed<ChatMessage[]>([]);
  const [input, setInput] = useStateEmbed('');
  const [isLoading, setIsLoading] = useStateEmbed(false);
  const [error, setError] = useStateEmbed<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffectEmbed(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (messageText?: string) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    setInput('');
    setError(null);

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch(`${apiUrl}/api/v1/inventory/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${response.status}`);
      }

      const data: ChatResponse = await response.json();

      if (data.success) {
        // Parse chart data from response
        const chartData = parseChartDataFromMessage(data.response);
        // Remove chart JSON from display content for cleaner view
        const cleanContent = chartData.length > 0
          ? removeChartDataFromMessage(data.response)
          : data.response;

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: cleanContent,
          timestamp: new Date(),
          toolsUsed: data.tools_used,
          chartData: chartData.length > 0 ? chartData as ChartDataType[] : undefined,
          usage: data.usage,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error('Error processing query');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido';
      setError(errorMsg);
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Lo siento, hubo un error: ${errorMsg}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Quick Actions */}
      {messages.length === 0 && (
        <div className="px-3 py-2 bg-gray-50 border-b shrink-0">
          <p className="text-xs text-gray-500 mb-2">Preguntas rapidas:</p>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => sendMessage(action.query)}
                disabled={isLoading}
                className="text-xs bg-white border border-gray-200 hover:border-green-300 hover:bg-green-50 px-2.5 py-1 rounded-full transition-colors disabled:opacity-50"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="space-y-3">
            {/* Welcome Message */}
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-100">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-800 font-medium mb-2">
                    Hola! Soy tu asistente de Grana. Puedo ayudarte con:
                  </p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                      <span><strong>Inventario:</strong> Stock total, por bodega o producto</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                      <span><strong>Alertas:</strong> Vencimientos y stock critico</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                      <span><strong>Ventas:</strong> Top productos y analisis por canal</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                      <span><strong>📊 Gráficos:</strong> Visualizaciones de ventas y proyecciones</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Example Queries */}
            <div className="bg-white rounded-xl p-3 border border-gray-200">
              <p className="text-xs font-medium text-gray-700 mb-2">Prueba preguntar:</p>
              <div className="space-y-1.5 text-xs text-gray-600">
                <p className="cursor-pointer hover:text-green-600" onClick={() => sendMessage('Cuanto stock total tenemos?')}>"Cuanto stock total tenemos?"</p>
                <p className="cursor-pointer hover:text-green-600" onClick={() => sendMessage('Que productos estan por vencer?')}>"Que productos estan por vencer?"</p>
                <p className="cursor-pointer hover:text-green-600" onClick={() => sendMessage('Top 10 productos mas vendidos')}>"Top 10 productos mas vendidos"</p>
                <p className="cursor-pointer hover:text-green-600" onClick={() => sendMessage('Cuantos dias de stock tenemos de barras?')}>"Cuantos dias de stock de barras?"</p>
              </div>
            </div>

            {/* Warehouse Codes - Compact */}
            <div className="bg-gray-50 rounded-lg p-2 border border-gray-100">
              <p className="text-[10px] font-medium text-gray-500 mb-1">Bodegas disponibles:</p>
              <p className="text-[10px] text-gray-400">
                Packner • Amplifica Centro/La Reina/Lo Barnechea/Quilicura • Orinoco • MercadoLibre
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[90%] rounded-2xl px-3 py-2 ${
                message.role === 'user'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {message.role === 'user' ? (
                <div className="text-sm whitespace-pre-wrap">{message.content}</div>
              ) : (
                <div className="text-sm">
                  {/* Render charts first if present */}
                  {message.chartData && message.chartData.length > 0 && (
                    <div className="mb-3 space-y-3">
                      {message.chartData.map((chart, idx) => (
                        <ChatChart
                          key={`chart-${message.id}-${idx}`}
                          data={chart as Parameters<typeof ChatChart>[0]['data']}
                          compact={true}
                        />
                      ))}
                    </div>
                  )}
                  {/* Render text content */}
                  {message.content && (
                    <div className="prose prose-sm max-w-none prose-table:text-xs">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: ({ children }) => (
                            <div className="overflow-x-auto my-2">
                              <table className="min-w-full border-collapse border border-gray-300 text-xs">
                                {children}
                              </table>
                            </div>
                          ),
                          thead: ({ children }) => <thead className="bg-gray-200">{children}</thead>,
                          th: ({ children }) => (
                            <th className="border border-gray-300 px-2 py-1 text-left font-semibold text-gray-700">{children}</th>
                          ),
                          td: ({ children }) => (
                            <td className="border border-gray-300 px-2 py-1 text-gray-600">{children}</td>
                          ),
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
                          li: ({ children }) => <li className="text-gray-700">{children}</li>,
                          code: ({ children }) => (
                            <code className="bg-gray-200 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              )}

              {message.toolsUsed && message.toolsUsed.length > 0 && (
                <p className="mt-1 pt-1 border-t border-gray-200 text-xs text-gray-500 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {message.toolsUsed.join(', ')}
                </p>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl px-3 py-2">
              <div className="flex items-center gap-2 text-gray-500">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-xs">Consultando...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Clear button (only when messages exist) */}
      {messages.length > 0 && (
        <div className="px-3 py-1 border-t bg-gray-50 shrink-0">
          <button
            onClick={clearConversation}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Limpiar conversacion
          </button>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t bg-white shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Escribe tu pregunta..."
            className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={() => sendMessage()}
            disabled={isLoading || !input.trim()}
            className="bg-green-600 text-white px-4 py-2 rounded-xl hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
