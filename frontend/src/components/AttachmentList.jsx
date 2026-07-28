import React from "react";
import { Download, Image as ImageIcon, FileText } from "lucide-react";
import { downloadFile, fileImgSrc, humanSize } from "@/lib/uploads";
import EmptyState from "@/components/EmptyState";

export default function AttachmentList({ attachments = [] }) {
  if (!attachments || attachments.length === 0) {
    return <div className="text-sm text-muted-foreground italic">No attachments yet.</div>;
  }
  const images = attachments.filter((a) => (a.content_type || "").startsWith("image/"));
  const files = attachments.filter((a) => !(a.content_type || "").startsWith("image/"));
  return (
    <div className="space-y-3" data-testid="attachment-list">
      {images.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {images.map((a) => (
            <button
              key={a.id}
              onClick={() => downloadFile(a.id, a.filename)}
              className="group relative rounded-md overflow-hidden border border-border hover-lift"
              data-testid={`attachment-image-${a.id}`}
            >
              <img src={fileImgSrc(a.id)} alt={a.filename} className="w-full h-24 object-cover" />
              <div className="absolute inset-x-0 bottom-0 bg-black/60 text-white text-[10px] px-2 py-1 truncate opacity-0 group-hover:opacity-100 transition-opacity">
                {a.filename}
              </div>
            </button>
          ))}
        </div>
      )}
      {files.length > 0 && (
        <div className="space-y-1.5">
          {files.map((a) => (
            <button
              key={a.id}
              onClick={() => downloadFile(a.id, a.filename)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md border border-border hover:bg-muted transition-colors text-left"
              data-testid={`attachment-file-${a.id}`}
            >
              <FileText className="w-4 h-4 text-primary shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{a.filename}</div>
                <div className="text-[11px] text-muted-foreground">{humanSize(a.size)}</div>
              </div>
              <Download className="w-4 h-4 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
