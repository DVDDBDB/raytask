import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { AUTH } from "@/constants/testIds";
import api from "@/lib/api";

export default function Signup() {
  const nav = useNavigate();
  const { signup } = useAuth();
  const [form, setForm] = useState({
    email: "", password: "", first_name: "", last_name: "", designation: "Other",
  });
  const [designations, setDesignations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/settings").then((r) => setDesignations(r.data.designations || [])).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await signup(form);
      toast.success("Signup received — await Super Admin approval.");
      nav("/login");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Signup failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-10">
      <form onSubmit={submit} className="w-full max-w-md space-y-5 card-flat p-8">
        <div>
          <div className="text-overline mb-2">Request access</div>
          <h2 className="text-3xl font-semibold" style={{ fontFamily: "Outfit" }}>
            Join Raybotix Digital
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Your account will be reviewed by a Super Admin before you can sign in.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>First name</Label>
            <Input
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              data-testid={AUTH.signupFirstName}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label>Last name</Label>
            <Input
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Email</Label>
          <Input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            data-testid={AUTH.signupEmail}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label>Password</Label>
          <Input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            data-testid={AUTH.signupPassword}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label>Designation</Label>
          <Select value={form.designation} onValueChange={(v) => setForm({ ...form, designation: v })}>
            <SelectTrigger data-testid={AUTH.signupDesignation}><SelectValue /></SelectTrigger>
            <SelectContent>
              {designations.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button
          type="submit"
          disabled={loading}
          className="w-full rounded-full"
          data-testid={AUTH.signupSubmit}
        >
          {loading ? "Submitting…" : "Request access"}
        </Button>
        <p className="text-sm text-center text-muted-foreground">
          Already have access? <Link to="/login" className="text-primary hover:underline">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
