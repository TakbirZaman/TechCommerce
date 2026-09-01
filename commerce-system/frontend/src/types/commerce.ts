export type PaymentMethod = "BKASH" | "NAGAD" | "SSLCOMMERZ";

export type OrderStatus =
  | "PENDING"
  | "PAYMENT_PENDING"
  | "PAID"
  | "PROCESSING"
  | "SHIPPED"
  | "DELIVERED"
  | "CANCELLED"
  | "REFUND_REQUESTED"
  | "REFUNDED";

export type PaymentStatus = "UNPAID" | "INITIATED" | "PENDING" | "PAID" | "FAILED" | "REFUNDED";

export interface CartItem {
  id: number;
  product_id: number;
  product_name: string;
  product_image_url: string | null;
  unit_price: string; // Decimal serialized as string by the API — never parsed as a source of truth client-side
  quantity: number;
  subtotal: string;
  available_stock: number;
}

export interface Cart {
  items: CartItem[];
  subtotal: string;
  total_items: number;
}

export interface DeliveryInfo {
  full_name: string;
  phone: string;
  address: string;
  city: string;
  area: string;
  postal_code?: string;
}

export interface OrderItem {
  product_id: number;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
}

export interface Order {
  id: number;
  order_number: string;
  subtotal: string;
  discount: string;
  delivery_charge: string;
  total_amount: string;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  order_status: OrderStatus;
  shipping_full_name: string;
  shipping_phone: string;
  shipping_address: string;
  shipping_city: string;
  shipping_area: string;
  shipping_postal_code: string | null;
  items: OrderItem[];
  created_at: string;
}

export interface OrderSummary {
  id: number;
  order_number: string;
  total_amount: string;
  payment_status: PaymentStatus;
  order_status: OrderStatus;
}

export interface PaymentInitiateResponse {
  payment_id: number;
  redirect_url: string | null;
  gateway_transaction_id: string | null;
}
