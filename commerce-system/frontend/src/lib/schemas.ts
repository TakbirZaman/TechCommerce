import { z } from "zod";

export const deliveryInfoSchema = z.object({
  full_name: z.string().min(2, "Full name is required"),
  phone: z
    .string()
    .min(11, "Enter a valid phone number")
    .regex(/^\+?\d{10,14}$/, "Enter a valid phone number"),
  address: z.string().min(5, "Address is required"),
  city: z.string().min(2, "City is required"),
  area: z.string().min(2, "Area is required"),
  postal_code: z.string().optional(),
});

export type DeliveryInfoFormValues = z.infer<typeof deliveryInfoSchema>;
