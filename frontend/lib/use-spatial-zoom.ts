'use client';

import { useReducer, useCallback, useRef } from 'react';

// Types
export type ZoomLevel = 0 | 1 | 2;
export type ZoomDirection = 'idle' | 'zoom-in' | 'zoom-out';

export interface ZoomState {
  level: ZoomLevel;
  direction: ZoomDirection;
  warehouseCode: string | null;
  warehouseName: string | null;
  warehouseUpdateMethod: string | null;
  productSku: string | null;
  productName: string | null;
}

export interface Breadcrumb {
  label: string;
  level: ZoomLevel;
}

type ZoomAction =
  | { type: 'ZOOM_INTO_WAREHOUSE'; code: string; name: string; updateMethod: string }
  | { type: 'ZOOM_INTO_PRODUCT'; sku: string; name: string }
  | { type: 'ZOOM_OUT' }
  | { type: 'ZOOM_TO_LEVEL'; level: ZoomLevel }
  | { type: 'TRANSITION_COMPLETE' };

const initialState: ZoomState = {
  level: 0,
  direction: 'idle',
  warehouseCode: null,
  warehouseName: null,
  warehouseUpdateMethod: null,
  productSku: null,
  productName: null,
};

function zoomReducer(state: ZoomState, action: ZoomAction): ZoomState {
  switch (action.type) {
    case 'ZOOM_INTO_WAREHOUSE':
      return {
        ...state,
        level: 1,
        direction: 'zoom-in',
        warehouseCode: action.code,
        warehouseName: action.name,
        warehouseUpdateMethod: action.updateMethod,
        productSku: null,
        productName: null,
      };

    case 'ZOOM_INTO_PRODUCT':
      return {
        ...state,
        level: 2,
        direction: 'zoom-in',
        productSku: action.sku,
        productName: action.name,
      };

    case 'ZOOM_OUT': {
      if (state.level === 2) {
        return {
          ...state,
          level: 1,
          direction: 'zoom-out',
          productSku: null,
          productName: null,
        };
      }
      if (state.level === 1) {
        return {
          ...state,
          level: 0,
          direction: 'zoom-out',
          warehouseCode: null,
          warehouseName: null,
          warehouseUpdateMethod: null,
          productSku: null,
          productName: null,
        };
      }
      return state;
    }

    case 'ZOOM_TO_LEVEL': {
      if (action.level >= state.level) return state;
      const direction: ZoomDirection = 'zoom-out';
      if (action.level === 0) {
        return {
          ...initialState,
          direction,
        };
      }
      if (action.level === 1) {
        return {
          ...state,
          level: 1,
          direction,
          productSku: null,
          productName: null,
        };
      }
      return state;
    }

    case 'TRANSITION_COMPLETE':
      return { ...state, direction: 'idle' };

    default:
      return state;
  }
}

const TRANSITION_DURATION = 450;

export function useSpatialZoom() {
  const [state, dispatch] = useReducer(zoomReducer, initialState);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleTransitionComplete = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      dispatch({ type: 'TRANSITION_COMPLETE' });
    }, TRANSITION_DURATION);
  }, []);

  const zoomIntoWarehouse = useCallback(
    (code: string, name: string, updateMethod: string) => {
      dispatch({ type: 'ZOOM_INTO_WAREHOUSE', code, name, updateMethod });
      scheduleTransitionComplete();
    },
    [scheduleTransitionComplete],
  );

  const zoomIntoProduct = useCallback(
    (sku: string, name: string) => {
      dispatch({ type: 'ZOOM_INTO_PRODUCT', sku, name });
      scheduleTransitionComplete();
    },
    [scheduleTransitionComplete],
  );

  const zoomOut = useCallback(() => {
    dispatch({ type: 'ZOOM_OUT' });
    scheduleTransitionComplete();
  }, [scheduleTransitionComplete]);

  const zoomToLevel = useCallback(
    (level: ZoomLevel) => {
      dispatch({ type: 'ZOOM_TO_LEVEL', level });
      scheduleTransitionComplete();
    },
    [scheduleTransitionComplete],
  );

  const animationClass =
    state.direction === 'zoom-in'
      ? 'animate-scope-zoom-in'
      : state.direction === 'zoom-out'
        ? 'animate-scope-zoom-out'
        : '';

  const breadcrumbs: Breadcrumb[] = [{ label: 'Bodegas', level: 0 }];
  if (state.level >= 1 && state.warehouseName) {
    breadcrumbs.push({ label: state.warehouseName, level: 1 });
  }
  if (state.level >= 2 && state.productName) {
    breadcrumbs.push({ label: state.productName, level: 2 });
  }

  return {
    state,
    zoomIntoWarehouse,
    zoomIntoProduct,
    zoomOut,
    zoomToLevel,
    animationClass,
    breadcrumbs,
  };
}
