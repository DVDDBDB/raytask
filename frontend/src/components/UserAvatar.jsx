import React from "react";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { initials } from "@/lib/format";

export function UserAvatar({ user, size = 32, className }) {
  if (!user) {
    return (
      <div
        className={cn("rounded-full bg-muted border border-border", className)}
        style={{ width: size, height: size }}
      />
    );
  }
  const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
  return (
    <Avatar
      className={cn("border border-border", className)}
      style={{ width: size, height: size }}
    >
      {user.avatar_url ? <AvatarImage src={user.avatar_url} alt={name} /> : null}
      <AvatarFallback className="text-[11px] bg-muted text-foreground">
        {initials(name)}
      </AvatarFallback>
    </Avatar>
  );
}
