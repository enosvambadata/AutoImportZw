"use client";

import { Gavel } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Disclaimer } from "@/components/domain";
import { Button, Card, CardBody, Field, Input } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";

const DEMO = [
  { label: "Administrator", email: "admin@example.com" },
  { label: "Buyer / Appraiser", email: "buyer@example.com" },
  { label: "Viewer", email: "viewer@example.com" },
];

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("Password123!");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 p-4">
      <div className="w-full max-w-md space-y-4">
        <div className="flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Gavel size={22} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">AutoBid Intelligence</h1>
            <p className="text-sm text-slate-500">Auction buying decisions, made with discipline.</p>
          </div>
        </div>

        <Card>
          <CardBody className="space-y-4">
            <form onSubmit={onSubmit} className="space-y-4">
              <Field label="Email">
                <Input
                  type="email"
                  value={email}
                  autoComplete="username"
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Field>
              <Field label="Password">
                <Input
                  type="password"
                  value={password}
                  autoComplete="current-password"
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field>
              {error && (
                <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                  {error}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
              <button type="button" className="w-full text-center text-xs text-slate-500 hover:text-slate-700">
                Forgot your password?
              </button>
            </form>

            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <p className="mb-1 font-medium text-slate-700">Demo logins (password: Password123!)</p>
              <div className="space-y-1">
                {DEMO.map((d) => (
                  <button
                    key={d.email}
                    type="button"
                    onClick={() => setEmail(d.email)}
                    className="block w-full text-left hover:text-brand-700"
                  >
                    {d.label}: <span className="font-mono">{d.email}</span>
                  </button>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>
        <Disclaimer compact />
      </div>
    </div>
  );
}
