import React from "react";

export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="card-flat p-12 text-center flex flex-col items-center gap-3">
      {Icon && (
        <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center">
          <Icon className="w-6 h-6 text-muted-foreground" />
        </div>
      )}
      <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>{title}</h3>
      {description && <p className="text-sm text-muted-foreground max-w-md">{description}</p>}
      {action}
    </div>
  );
}
