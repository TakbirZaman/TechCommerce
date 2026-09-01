import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Store",
  description: "Cart, checkout, and order management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <Providers>
          <div className="mx-auto max-w-4xl px-4 py-8">{children}</div>
        </Providers>
      </body>
    </html>
  );
}
