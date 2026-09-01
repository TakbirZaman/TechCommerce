"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { RecommendationCard } from "@/components/RecommendationCard";
import {
  AdvisorMessageResponse,
  sendAdvisorMessage,
  UserRequirement,
} from "@/lib/api";

interface ChatTurn {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTED_USE_CASES = [
  "Programming",
  "Gaming",
  "Machine Learning",
  "Video Editing",
  "University",
  "Business",
  "General Use",
];

function RequirementSummary({ requirement }: { requirement: UserRequirement }) {
  return (
    <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <p className="font-semibold text-slate-800">Based on what you told me:</p>
      <ul className="mt-1 space-y-0.5">
        <li>Category: {requirement.category}</li>
        {requirement.budget_max && <li>Budget: up to ৳{requirement.budget_max.toLocaleString()}</li>}
        {requirement.use_cases.length > 0 && (
          <li>Use cases: {requirement.use_cases.join(", ")}</li>
        )}
      </ul>
      <p className="mt-2 text-xs text-slate-400">
        These are the strongest matches given your budget and stated preferences — not a
        guaranteed "best" choice.
      </p>
    </div>
  );
}

export default function AdvisorPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([
    {
      role: "assistant",
      text: "Tell us what you're looking for — e.g. \"a laptop under 100k for programming and gaming\".",
    },
  ]);
  const [result, setResult] = useState<AdvisorMessageResponse | null>(null);

  const mutation = useMutation({
    mutationFn: (message: string) => sendAdvisorMessage(sessionId, message),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setResult(data);
      const assistantText =
        data.follow_up_question ??
        (data.recommendations
          ? `Here are ${data.recommendations.recommendations.length} matches for you.`
          : "I couldn't find any matches for that yet — try adjusting your budget or category.");
      setTurns((prev) => [...prev, { role: "assistant", text: assistantText }]);
    },
    onError: (error: Error) => {
      setTurns((prev) => [...prev, { role: "assistant", text: `Something went wrong: ${error.message}` }]);
    },
  });

  function handleSend(message: string) {
    if (!message.trim()) return;
    setTurns((prev) => [...prev, { role: "user", text: message }]);
    setInput("");
    mutation.mutate(message);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col px-4 py-10">
      <h1 className="mb-6 text-2xl font-bold text-slate-900">Product Advisor</h1>

      <div className="mb-6 flex-1 space-y-3 overflow-y-auto">
        {turns.map((turn, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
              turn.role === "user"
                ? "ml-auto bg-slate-900 text-white"
                : "bg-white text-slate-800 shadow-sm"
            }`}
          >
            {turn.text}
          </div>
        ))}
        {mutation.isPending && (
          <div className="max-w-[85%] rounded-2xl bg-white px-4 py-2 text-sm text-slate-400 shadow-sm">
            Thinking…
          </div>
        )}
      </div>

      {result?.follow_up_question?.toLowerCase().includes("use it for") && (
        <div className="mb-4 flex flex-wrap gap-2">
          {SUGGESTED_USE_CASES.map((option) => (
            <button
              key={option}
              onClick={() => handleSend(option)}
              className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
            >
              {option}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="mb-8 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell us what you're looking for..."
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>

      {result?.requirement && <RequirementSummary requirement={result.requirement} />}

      {result?.recommendations && (
        <div className="space-y-4 pb-10">
          {result.recommendations.recommendations.map((product) => (
            <RecommendationCard key={product.product_id} product={product} />
          ))}
        </div>
      )}
    </main>
  );
}
