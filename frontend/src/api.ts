export const TOKEN_KEY = "eve_jwt";

/** Dispatched on 401 so AuthProvider can reset in-memory auth state. */
export const UNAUTHORIZED_EVENT = "eve:unauthorized";

function notifyUnauthorized(): void {
  try {
    if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
  } catch {
    // non-browser / dispatch unavailable — storage already cleared below
  }
}

export const API_BASE = (
  import.meta.env.VITE_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function parseErrorMessage(data: unknown, fallback: string): string {
  if (data !== null && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // FastAPI validation errors: [{loc, msg, ...}]
      const msgs = detail
        .map((d) =>
          d && typeof d === "object" && "msg" in d
            ? String((d as { msg: unknown }).msg)
            : null,
        )
        .filter(Boolean);
      if (msgs.length > 0) return msgs.join("; ");
    }
  }
  return fallback;
}

export async function request<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = new Headers(opts.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (opts.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });

  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("eve_email");
    notifyUnauthorized();
  }

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data: unknown = await res.json();
      message = parseErrorMessage(data, message);
    } catch {
      // non-JSON error body — keep fallback message
    }
    throw new ApiError(message, res.status);
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export interface SignupResponse {
  id: string | number;
  name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

async function signup(
  name: string,
  email: string,
  password: string,
): Promise<SignupResponse> {
  return request<SignupResponse>("/auth/signup/", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

async function login(email: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams({ username: email, password });
  return request<LoginResponse>("/auth/login/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
}

export interface Centre {
  id: number;
  name: string;
  location: string;
}

export interface CentreTest {
  id: number;
  name: string;
  price: number;
}

export interface CentreDetail extends Centre {
  tests: CentreTest[];
}

export interface Offering {
  id: number;
  name: string;
  price: number;
  centre_id: number;
}

export interface Booking {
  id: number;
  centre_id: number;
  test_id: number;
  appointment_datetime: string;
  status: string;
  amount: number;
}

async function listCentres(): Promise<Centre[]> {
  return request<Centre[]>("/centres/");
}

async function centreDetail(id: string | number): Promise<CentreDetail> {
  return request<CentreDetail>(`/centres/${id}/`);
}

async function listTests(params?: {
  centre_id?: number;
  location?: string;
}): Promise<Offering[]> {
  const q = new URLSearchParams();
  if (params?.centre_id !== undefined) q.set("centre_id", String(params.centre_id));
  if (params?.location) q.set("location", params.location);
  const suffix = q.toString() ? `?${q.toString()}` : "/";
  return request<Offering[]>(`/tests${suffix}`);
}

async function createBooking(
  centre_id: number,
  test_id: number,
  appointment_datetime: string,
): Promise<Booking> {
  return request<Booking>("/bookings/", {
    method: "POST",
    body: JSON.stringify({ centre_id, test_id, appointment_datetime }),
  });
}

export interface PaymentResult {
  payment: {
    id: number;
    booking_id: number;
    amount: number;
    status: string;
    provider_reference: string;
  };
  booking_status: string;
}

export interface MockChargeResult {
  outcome: string;
  event_id: string;
  provider_reference: string;
  payment_id: number;
  booking_status: string;
}

async function myBookings(): Promise<Booking[]> {
  return request<Booking[]>("/bookings/");
}

async function getBooking(id: string | number): Promise<Booking> {
  return request<Booking>(`/bookings/${id}/`);
}

async function cancelBooking(id: string | number): Promise<Booking> {
  return request<Booking>(`/bookings/${id}/cancel/`, { method: "PATCH" });
}

async function rescheduleBooking(
  id: string | number,
  appointment_datetime: string,
): Promise<Booking> {
  return request<Booking>(`/bookings/${id}/reschedule/`, {
    method: "PATCH",
    body: JSON.stringify({ appointment_datetime }),
  });
}

async function payBooking(
  id: string | number,
  simulate: "success" | "fail",
): Promise<PaymentResult> {
  return request<PaymentResult>("/payments/", {
    method: "POST",
    body: JSON.stringify({ booking_id: Number(id), simulate }),
  });
}

async function mockCharge(id: string | number): Promise<MockChargeResult> {
  return request<MockChargeResult>("/payments/mock/charge", {
    method: "POST",
    body: JSON.stringify({ booking_id: Number(id) }),
  });
}

export interface AdminBooking {
  id: number;
  user_id: number;
  user_email: string;
  centre_id: number;
  centre_name: string;
  test_id: number;
  test_name: string;
  appointment_datetime: string;
  status: string;
  amount: number;
}

export interface AdminPayment {
  id: number;
  booking_id: number;
  amount: number;
  status: string;
  provider_reference: string;
}

export interface AdminCentre {
  id: number;
  name: string;
  location: string;
}

export interface AdminTest {
  id: number;
  name: string;
}

export interface AdminOffering {
  id: number;
  centre_id: number;
  test_id: number;
  price: number;
}

async function adminBookings(params?: {
  status?: string;
  centre_id?: number;
  user?: string;
  limit?: number;
  offset?: number;
  order?: "asc" | "desc";
}): Promise<AdminBooking[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.centre_id !== undefined) q.set("centre_id", String(params.centre_id));
  if (params?.user) q.set("user", params.user);
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  if (params?.offset !== undefined) q.set("offset", String(params.offset));
  if (params?.order) q.set("order", params.order);
  const suffix = q.toString() ? `?${q.toString()}` : "";
  return request<AdminBooking[]>(`/admin/bookings${suffix}`);
}

export interface AdminBookingStats {
  total: number;
  counts: Record<string, number>;
  confirmed_sum: number;
}

async function adminBookingStats(params?: {
  status?: string;
  centre_id?: number;
  user?: string;
}): Promise<AdminBookingStats> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.centre_id !== undefined) q.set("centre_id", String(params.centre_id));
  if (params?.user) q.set("user", params.user);
  const suffix = q.toString() ? `?${q.toString()}` : "";
  return request<AdminBookingStats>(`/admin/bookings/stats${suffix}`);
}

async function adminPayments(params?: {
  booking_id?: number;
  limit?: number;
  offset?: number;
}): Promise<AdminPayment[]> {
  const q = new URLSearchParams();
  if (params?.booking_id !== undefined) q.set("booking_id", String(params.booking_id));
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  if (params?.offset !== undefined) q.set("offset", String(params.offset));
  const suffix = q.toString() ? `?${q.toString()}` : "";
  return request<AdminPayment[]>(`/admin/payments${suffix}`);
}

async function adminTests(): Promise<AdminTest[]> {
  return request<AdminTest[]>("/admin/tests");
}

async function adminCreateCentre(name: string, location: string): Promise<AdminCentre> {
  return request<AdminCentre>("/admin/centres", {
    method: "POST",
    body: JSON.stringify({ name, location }),
  });
}

async function adminUpdateCentre(
  id: string | number,
  payload: { name?: string; location?: string },
): Promise<AdminCentre> {
  return request<AdminCentre>(`/admin/centres/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

async function adminDeleteCentre(id: string | number): Promise<void> {
  return request<void>(`/admin/centres/${id}`, { method: "DELETE" });
}

async function adminCreateTest(name: string): Promise<AdminTest> {
  return request<AdminTest>("/admin/tests", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

async function adminUpdateTest(
  id: string | number,
  payload: { name: string },
): Promise<AdminTest> {
  return request<AdminTest>(`/admin/tests/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

async function adminDeleteTest(id: string | number): Promise<void> {
  return request<void>(`/admin/tests/${id}`, { method: "DELETE" });
}

async function adminUpsertOffering(
  centre_id: number,
  test_id: number,
  price: number,
): Promise<AdminOffering> {
  return request<AdminOffering>("/admin/offerings", {
    method: "PUT",
    body: JSON.stringify({ centre_id, test_id, price }),
  });
}

export const api = { signup, login, listCentres, centreDetail, listTests, createBooking, myBookings, getBooking, cancelBooking, rescheduleBooking, payBooking, mockCharge, adminBookings, adminBookingStats, adminPayments, adminTests, adminCreateCentre, adminUpdateCentre, adminDeleteCentre, adminCreateTest, adminUpdateTest, adminDeleteTest, adminUpsertOffering };
