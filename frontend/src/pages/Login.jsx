import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { AUTH } from "@/constants/testIds";
import { ArrowRight } from "lucide-react";

export default function Login() {
  const nav = useNavigate();
  const { login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => { if (user) nav("/"); }, [user, nav]);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      nav("/");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Invalid credentials");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-[46%] p-12 bg-[#110F0F] text-[#F5F2F0] relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1542966336-22953b5f7404?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwxfHxkYXJrJTIwZW1iZXIlMjByZWQlMjBhYnN0cmFjdCUyMHRleHR1cmV8ZW58MHx8fHwxNzgyODgzNzE0fDA&ixlib=rb-4.1.0&q=85')",
            backgroundSize: "cover", backgroundPosition: "center",
          }}
        />
        <div className="relative">
          <div className="inline-flex items-center gap-2.5">
            <div className="w-11 h-11 rounded-lg border border-[#FF4D5A]/40 flex items-center justify-center">
              <span className="text-[#FF4D5A] text-xl font-bold" style={{ fontFamily: "Outfit" }}>R</span>
            </div>
            <div>
              <div className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Raybotix Digital</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-white/60">workflow platform</div>
            </div>
          </div>
        </div>
        <div className="relative space-y-4 max-w-md">
          <h1 className="text-4xl xl:text-5xl font-semibold leading-tight" style={{ fontFamily: "Outfit" }}>
            Every task,<br />
            <span className="text-[#FF4D5A]">every second,</span><br />
            accounted for.
          </h1>
          <p className="text-white/70 text-sm leading-relaxed">
            Assign work, watch it move between writers, designers, editors and managers,
            and see exactly what each hour costs your agency.
          </p>
        </div>
        <div className="relative text-[11px] uppercase tracking-[0.24em] text-white/50">
          © Raybotix Digital
        </div>
      </div>

      {/* Form panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-10">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6">
          <div>
            <div className="text-overline mb-2">Sign in</div>
            <h2 className="text-3xl font-semibold" style={{ fontFamily: "Outfit" }}>
              Welcome back.
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Enter your credentials to continue.
            </p>
          </div>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@raybotix.com"
                data-testid={AUTH.loginEmail}
                autoComplete="email"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Password</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                data-testid={AUTH.loginPassword}
                autoComplete="current-password"
                required
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 text-muted-foreground cursor-pointer">
                <Checkbox checked={remember} onCheckedChange={setRemember} />
                Remember me
              </label>
              <Link to="/signup" className="text-primary hover:underline">Need access?</Link>
            </div>
          </div>
          <Button
            type="submit"
            disabled={loading}
            className="w-full rounded-full gap-2"
            data-testid={AUTH.loginSubmit}
          >
            {loading ? "Signing in…" : "Sign in"} <ArrowRight className="w-4 h-4" />
          </Button>
          <div className="text-[11px] text-muted-foreground text-center border border-dashed border-border rounded-md p-3">
            <div className="font-semibold text-foreground">Demo — Super Admin</div>
            superadmin@raybotix.com &nbsp;·&nbsp; Admin@123
          </div>
        </form>
      </div>
    </div>
  );
}
