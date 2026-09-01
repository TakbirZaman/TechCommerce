import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-bold">Product Intelligence</h1>
      <Link href="/advisor" className="rounded-lg bg-slate-900 px-4 py-2 text-white">
        Try the AI Advisor
      </Link>
    </main>
  );
}
