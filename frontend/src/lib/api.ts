/**
 * API Client for TechCommerce
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
}

async function fetchAPI<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', headers = {}, body } = options;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (typeof window !== 'undefined') {
    // Add auth token if available
    const token = localStorage.getItem('access_token');
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }

    // Add session ID for cart/commerce endpoints
    if (endpoint.includes('/commerce/')) {
      let sessionId = localStorage.getItem('session_id');
      if (!sessionId) {
        sessionId = crypto.randomUUID();
        localStorage.setItem('session_id', sessionId);
      }
      requestHeaders['X-Session-ID'] = sessionId;
    }
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth API
export const auth = {
  register: (data: { email: string; password: string; full_name: string; phone?: string }) =>
    fetchAPI('/api/v1/auth/register', { method: 'POST', body: data }),
  
  login: async (email: string, password: string) => {
    const result = await fetchAPI<{ access_token: string; refresh_token: string; user: any }>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', result.access_token);
      localStorage.setItem('refresh_token', result.refresh_token);
    }
    return result;
  },
  
  refresh: (refreshToken: string) =>
    fetchAPI('/api/v1/auth/refresh', { method: 'POST', body: { refresh_token: refreshToken } }),
  
  logout: async (refreshToken?: string) => {
    const token = refreshToken || (typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null);
    if (token) {
      await fetchAPI('/api/v1/auth/logout', { method: 'POST', body: { refresh_token: token } }).catch(() => {});
    }
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },
  
  me: () => fetchAPI<any>('/api/v1/auth/me'),
};

// Catalog API
export const catalog = {
  brands: () => fetchAPI<any[]>('/api/v1/catalog/brands'),
  
  categories: () => fetchAPI<any[]>('/api/v1/catalog/categories'),
  
  category: (slug: string) => fetchAPI<any>(`/api/v1/catalog/categories/${slug}`),
  
  specTemplate: (slug: string) => fetchAPI<any>(`/api/v1/catalog/categories/${slug}/spec-template`),
  
  products: (params?: {
    category?: string;
    brand?: string;
    min_price?: number;
    max_price?: number;
    search?: string;
    sort?: string;
    page?: number;
    page_size?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.set(key, String(value));
        }
      });
    }
    const query = searchParams.toString();
    return fetchAPI<any[]>(`/api/v1/catalog/products${query ? `?${query}` : ''}`);
  },
  
  product: (slug: string) => fetchAPI<any>(`/api/v1/catalog/products/${slug}`),
  
  search: (q: string, params?: { category?: string; min_price?: number; max_price?: number }) => {
    const searchParams = new URLSearchParams({ q });
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.set(key, String(value));
        }
      });
    }
    return fetchAPI<any[]>(`/api/v1/catalog/search?${searchParams.toString()}`);
  },
  
  autocomplete: (q: string) =>
    fetchAPI<any>(`/api/v1/catalog/autocomplete?q=${encodeURIComponent(q)}`),
};

// Commerce API
export const commerce = {
  cart: () => fetchAPI<any>('/api/v1/commerce/cart'),
  
  addToCart: (productId: number, quantity: number = 1) =>
    fetchAPI<any>('/api/v1/commerce/cart/items', {
      method: 'POST',
      body: { product_id: productId, quantity },
    }),
  
  updateCartItem: (itemId: number, quantity: number) =>
    fetchAPI<any>(`/api/v1/commerce/cart/items/${itemId}`, {
      method: 'PUT',
      body: { quantity },
    }),
  
  removeFromCart: (itemId: number) =>
    fetchAPI<any>(`/api/v1/commerce/cart/items/${itemId}`, { method: 'DELETE' }),
  
  clearCart: () =>
    fetchAPI<any>('/api/v1/commerce/cart', { method: 'DELETE' }),
  
  checkout: (data: {
    full_name: string;
    email: string;
    phone: string;
    address: string;
    city: string;
    area: string;
    postal_code?: string;
    payment_method: string;
    discount_code?: string;
  }) => fetchAPI<any>('/api/v1/commerce/checkout', { method: 'POST', body: data }),
  
  trackOrder: (orderNumber: string, email: string) =>
    fetchAPI<any>('/api/v1/commerce/orders/track', {
      method: 'POST',
      body: { order_number: orderNumber, email },
    }),
};

// Comparison API
export const compare = {
  get: () => fetchAPI<any>('/api/v1/compare/current'),
  
  add: (productId: number) =>
    fetchAPI<any>('/api/v1/compare/add', {
      method: 'POST',
      body: { product_id: productId },
    }),
  
  remove: (itemId: number) =>
    fetchAPI<any>(`/api/v1/compare/items/${itemId}`, { method: 'DELETE' }),
  
  clear: () =>
    fetchAPI<any>('/api/v1/compare/clear', { method: 'DELETE' }),
  
  check: () => fetchAPI<any>('/api/v1/compare/check-compatibility'),
  
  winner: () => fetchAPI<any>('/api/v1/compare/winner'),
};

// PC Builder API
export const pcBuilder = {
  checkCompatibility: (components: { category: string; product_id: number }[]) =>
    fetchAPI<any>('/api/v1/pc-builder/check-compatibility', {
      method: 'POST',
      body: { components },
    }),
  
  calculateTotal: (productIds: number[]) =>
    fetchAPI<any>('/api/v1/pc-builder/calculate-total', {
      method: 'POST',
      body: { product_ids: productIds },
    }),
  
  suggestedComponents: (components: { category: string; product_id: number }[]) =>
    fetchAPI<any>('/api/v1/pc-builder/suggested-components', {
      method: 'POST',
      body: { components },
    }),
  
  create: (data: { name: string; components: { category: string; product_id: number }[] }) =>
    fetchAPI<any>('/api/v1/pc-builder/builds', {
      method: 'POST',
      body: data,
    }),
  
  builds: () => fetchAPI<any[]>('/api/v1/pc-builder/builds'),
  
  getBuild: (id: number) => fetchAPI<any>(`/api/v1/pc-builder/builds/${id}`),
};

// Advisor API
export const advisor = {
  recommend: (query: string, sessionId?: string) =>
    fetchAPI<any>('/api/v1/advisor/recommend', {
      method: 'POST',
      body: { query, session_id: sessionId },
    }),
  
  trending: (limit?: number) =>
    fetchAPI<any[]>(`/api/v1/advisor/trending${limit ? `?limit=${limit}` : ''}`),
  
  similar: (productId: number, limit?: number) =>
    fetchAPI<any[]>(`/api/v1/advisor/similar/${productId}${limit ? `?limit=${limit}` : ''}`),
};

// Admin API
export const admin = {
  dashboard: () => fetchAPI<any>('/api/v1/admin/dashboard'),
  
  products: (params?: { search?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.set(key, String(value));
      });
    }
    return fetchAPI<{ products: any[]; total: number; page: number; page_size: number }>(`/api/v1/admin/products?${searchParams.toString()}`);
  },
  
  createProduct: (data: any) => fetchAPI<any>('/api/v1/admin/products', { method: 'POST', body: data }),
  
  updateProduct: (id: number, data: any) => fetchAPI<any>(`/api/v1/admin/products/${id}`, { method: 'PUT', body: data }),
  
  deleteProduct: (id: number) => fetchAPI<any>(`/api/v1/admin/products/${id}`, { method: 'DELETE' }),
  
  uploadImage: async (file: File, productId?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    if (productId) formData.append('product_id', String(productId));
    
    const headers: Record<string, string> = {};
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE}/api/v1/admin/upload-image`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  },
  
  deleteImage: (id: number) => fetchAPI<any>(`/api/v1/admin/images/${id}`, { method: 'DELETE' }),
  
  orders: (params?: { status?: string; search?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.set(key, String(value));
      });
    }
    return fetchAPI<{ orders: any[]; total: number; page: number; page_size: number }>(`/api/v1/admin/orders?${searchParams.toString()}`);
  },
  
  updateOrder: (id: number, data: any) => fetchAPI<any>(`/api/v1/admin/orders/${id}/status`, { method: 'PUT', body: data }),
  
  coupons: () => fetchAPI<any[]>('/api/v1/admin/coupons'),
  
  createCoupon: (data: any) => fetchAPI<any>('/api/v1/admin/coupons', { method: 'POST', body: data }),
  
  updateCoupon: (id: number, data: any) => fetchAPI<any>(`/api/v1/admin/coupons/${id}`, { method: 'PUT', body: data }),
  
  deleteCoupon: (id: number) => fetchAPI<any>(`/api/v1/admin/coupons/${id}`, { method: 'DELETE' }),
  
  users: (params?: { search?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.set(key, String(value));
      });
    }
    return fetchAPI<{ users: any[]; total: number; page: number; page_size: number }>(`/api/v1/admin/users?${searchParams.toString()}`);
  },
  
  deliveryZones: () => fetchAPI<any[]>('/api/v1/admin/delivery-zones'),
  
  createDeliveryZone: (data: any) => fetchAPI<any>('/api/v1/admin/delivery-zones', { method: 'POST', body: data }),
  
  updateDeliveryZone: (id: number, data: any) => fetchAPI<any>(`/api/v1/admin/delivery-zones/${id}`, { method: 'PUT', body: data }),
  
  deleteDeliveryZone: (id: number) => fetchAPI<any>(`/api/v1/admin/delivery-zones/${id}`, { method: 'DELETE' }),
};
