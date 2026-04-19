import { Suspense } from "react";
import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <main className="shell min-h-screen">
      <div className="container relative flex min-h-screen items-center justify-center py-12">
        <Suspense
          fallback={
            <section className="groupbox w-full max-w-md p-6 md:p-8">
              <span className="groupbox__title">Sign in</span>
              <p className="text-sm text-muted">Loading...</p>
            </section>
          }
        >
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
