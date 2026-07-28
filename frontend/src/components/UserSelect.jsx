import React from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { userLabel } from "@/lib/format";

export default function UserSelect({ users = [], value, onChange, placeholder = "Select employee", showWorkload = true, testId = "user-select", disabled = false }) {
  return (
    <Select value={value || ""} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger data-testid={testId} className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {users.filter((u) => u.status === "active").map((u) => (
          <SelectItem key={u.id} value={u.id}>
            {userLabel(u, { showWorkload })}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
