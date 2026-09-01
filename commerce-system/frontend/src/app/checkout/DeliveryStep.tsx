"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { deliveryInfoSchema, type DeliveryInfoFormValues } from "@/lib/schemas";
import { useCheckoutWizard } from "@/hooks/useCheckoutWizard";

export function DeliveryStep() {
  const setDelivery = useCheckoutWizard((s) => s.setDelivery);
  const existing = useCheckoutWizard((s) => s.delivery);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<DeliveryInfoFormValues>({
    resolver: zodResolver(deliveryInfoSchema),
    defaultValues: existing ?? undefined,
  });

  return (
    <form
      className="space-y-4 rounded-xl bg-white p-6 shadow-sm"
      onSubmit={handleSubmit((values) => setDelivery(values))}
    >
      <h2 className="text-lg font-semibold">Delivery Information</h2>

      <Input label="Full name" {...register("full_name")} error={errors.full_name?.message} />
      <Input label="Phone" placeholder="01XXXXXXXXX" {...register("phone")} error={errors.phone?.message} />
      <Input label="Address" {...register("address")} error={errors.address?.message} />

      <div className="grid grid-cols-2 gap-4">
        <Input label="City" {...register("city")} error={errors.city?.message} />
        <Input label="Area" {...register("area")} error={errors.area?.message} />
      </div>

      <Input
        label="Postal code (optional)"
        {...register("postal_code")}
        error={errors.postal_code?.message}
      />

      <Button type="submit" className="w-full">
        Continue to Order Summary
      </Button>
    </form>
  );
}
