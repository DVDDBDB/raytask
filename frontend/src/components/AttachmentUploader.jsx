import React, { useRef, useState } from "react";
import { Upload, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { uploadFile, humanSize, fileImgSrc } from "@/lib/uploads";
import { cn } from "@/lib/utils";

/**
 * Drop-zone that uploads files immediately and calls `onChange(newList)` with the
 * updated attachment array `[{id, filename, content_type, size, url}]`.
 */
export default function AttachmentUploader({ value = [], onChange, testId = "attachment-uploader", compact = false }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(0);
  const inputRef = useRef(null);

  const doUpload = async (files) => {
    if (!files || files.length === 0) return;
    setUploading((n) => n + files.length);
    const uploaded = [];
    for (const f of files) {
      try {
        const meta = await uploadFile(f);
        uploaded.push(meta);
      } catch (e) {
        toast.error(`Upload failed: ${f.name} — ${e?.response?.data?.detail || e.message}`);
      } finally {
        setUploading((n) => n - 1);
      }
    }
    if (uploaded.length) {
      onChange && onChange([...(value || []), ...uploaded]);
      toast.success(`${uploaded.length} file${uploaded.length > 1 ? "s" : ""} attached`);
    }
  };

  const remove = (id) => onChange && onChange((value || []).filter((a) => a.id !== id));

  return (
    <div className="space-y-2" data-testid={testId}>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragOver(false);
          doUpload(Array.from(e.dataTransfer.files));
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "cursor-pointer rounded-md border-2 border-dashed p-4 text-center transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
          compact && "p-3",
        )}
        data-testid={`${testId}-dropzone`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => doUpload(Array.from(e.target.files || []))}
          data-testid={`${testId}-input`}
        />
        {uploading > 0 ? (
          <div className="flex items-center justify-center gap-2 text-sm text-primary">
            <Loader2 className="w-4 h-4 animate-spin" /> Uploading {uploading}…
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Upload className="w-4 h-4" />
            <span>
              <span className="text-primary font-semibold">Click to upload</span>
              {" "}or drop files here
            </span>
          </div>
        )}
      </div>

      {value?.length > 0 && (
        <div className="space-y-1.5">
          {value.map((a) => (
            <div key={a.id} className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2" data-testid={`attachment-${a.id}`}>
              {a.content_type?.startsWith("image/") ? (
                <img src={fileImgSrc(a.id)} alt={a.filename} className="w-9 h-9 rounded object-cover border border-border" />
              ) : (
                <div className="w-9 h-9 rounded bg-muted text-[10px] flex items-center justify-center font-semibold uppercase">
                  {(a.filename || "").split(".").pop().slice(0, 4)}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{a.filename}</div>
                <div className="text-[11px] text-muted-foreground">{humanSize(a.size)}</div>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); remove(a.id); }}
                className="text-muted-foreground hover:text-primary p-1 rounded hover:bg-muted"
                data-testid={`attachment-remove-${a.id}`}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
