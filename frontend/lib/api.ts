// Typed client for the intelligence-system FastAPI backend.
// Set NEXT_PUBLIC_API_BASE_URL in the environment to point at the deployed API.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Category = "laptop" | "smartphone" | "monitor";

export interface ScoredProduct {
  product_id: string;
  score: number;
  reasons: string[];
  tradeoffs: string[];
  component_scores: Record<string, number>;
}

export interface UserRequirement {
  category: Category;
  budget_min: number | null;
  budget_max: number | null;
  use_cases: string[];
  priorities: Record<string, number | null>;
  required_specs: Record<string, unknown>;
  preferred_brands: string[];
}

export interface RecommendationResponse {
  requirement: UserRequirement;
  recommendations: ScoredProduct[];
  candidates_considered: number;
  candidates_after_filtering: number;
  engine: string;
}

export interface AdvisorMessageResponse {
  session_id: string;
  follow_up_question: string | null;
  requirement: UserRequirement | null;
  recommendations: RecommendationResponse | null;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API error ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function sendAdvisorMessage(sessionId: string | null, message: string) {
  return postJson<AdvisorMessageResponse>("/api/v1/advisor/message", {
    session_id: sessionId,
    message,
  });
}

export function getRecommendations(params: {
  category: Category;
  budget?: number;
  use_cases?: string[];
  query?: string;
}) {
  return postJson<RecommendationResponse>("/api/v1/recommendations", params);
}
