"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";

/**
 * Section 13-14: review submission form. Note there is NO
 * "verified purchase" field anywhere in this form or its schema — that
 * is determined entirely server-side.
 */
const reviewSchema = z.object({
  rating: z.number().min(1).max(5),
  title: z.string().min(3).max(200),
  body: z.string().min(10).max(5000),
  pros: z.string().max(1000).optional(),
  cons: z.string().max(1000).optional(),
});
type ReviewFormValues = z.infer<typeof reviewSchema>;

export function ReviewForm({ productId }: { productId: number }) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ReviewFormValues>({ resolver: zodResolver(reviewSchema), defaultValues: { rating: 5 } });

  const mutation = useMutation({
    mutationFn: (values: ReviewFormValues) => apiPost(`/products/${productId}/reviews`, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", productId] });
      queryClient.invalidateQueries({ queryKey: ["rating", productId] });
      reset();
    },
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="space-y-4"
      aria-label="Write a review"
    >
      <div>
        <label htmlFor="rating" className="block text-sm font-medium">Rating</label>
        <select id="rating" {...register("rating", { valueAsNumber: true })} className="mt-1 rounded-md border border-input px-2 py-1">
          {[5, 4, 3, 2, 1].map((r) => (
            <option key={r} value={r}>{r} star{r > 1 ? "s" : ""}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="title" className="block text-sm font-medium">Title</label>
        <input id="title" {...register("title")} className="mt-1 w-full rounded-md border border-input px-3 py-2" />
        {errors.title && <p role="alert" className="text-xs text-destructive">{errors.title.message}</p>}
      </div>

      <div>
        <label htmlFor="body" className="block text-sm font-medium">Review</label>
        <textarea id="body" rows={4} {...register("body")} className="mt-1 w-full rounded-md border border-input px-3 py-2" />
        {errors.body && <p role="alert" className="text-xs text-destructive">{errors.body.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="pros" className="block text-sm font-medium">Pros (optional)</label>
          <textarea id="pros" rows={2} {...register("pros")} className="mt-1 w-full rounded-md border border-input px-3 py-2" />
        </div>
        <div>
          <label htmlFor="cons" className="block text-sm font-medium">Cons (optional)</label>
          <textarea id="cons" rows={2} {...register("cons")} className="mt-1 w-full rounded-md border border-input px-3 py-2" />
        </div>
      </div>

      {mutation.isError && (
        <p role="alert" className="text-sm text-destructive">
          Couldn&apos;t submit your review. You may have already reviewed this product.
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting || mutation.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {mutation.isPending ? "Submitting…" : "Submit review"}
      </button>
    </form>
  );
}
