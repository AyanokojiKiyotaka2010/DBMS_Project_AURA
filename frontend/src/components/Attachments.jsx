import React, { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Paperclip, X, FileImage, FilePdf, CaretLeft, CaretRight, DownloadSimple } from "@phosphor-icons/react";

const MAX_FILES = 3;
const MAX_BYTES = 2 * 1024 * 1024;

export function AttachmentPicker({ attachments, setAttachments, testidPrefix }) {
  const inputRef = React.useRef(null);

  const onPick = async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (attachments.length + files.length > MAX_FILES) {
      return toast.error(`Max ${MAX_FILES} attachments allowed`);
    }
    const encoded = [];
    for (const f of files) {
      if (f.size > MAX_BYTES) { toast.error(`${f.name} exceeds 2MB`); continue; }
      try {
        const data = await new Promise((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(String(r.result).split(",")[1] || "");
          r.onerror = () => reject(new Error("read failed"));
          r.readAsDataURL(f);
        });
        encoded.push({ name: f.name, mime: f.type || "application/octet-stream", data });
      } catch {
        toast.error(`Could not read ${f.name}`);
      }
    }
    if (encoded.length) {
      setAttachments([...attachments, ...encoded]);
      toast.success(`${encoded.length} file${encoded.length > 1 ? "s" : ""} attached`);
    }
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        data-testid={`${testidPrefix}-attach-btn`}
        onClick={() => inputRef.current?.click()}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-dashed border-edge text-xs text-ink-2 hover:text-ink hover:border-brand transition-colors"
      >
        <Paperclip size={13} />
        <span>Attach {attachments.length > 0 && `(${attachments.length})`}</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*,application/pdf"
        data-testid={`${testidPrefix}-attach-input`}
        onChange={onPick}
        className="hidden"
      />
      {attachments.map((a, i) => (
        <div
          key={i}
          data-testid={`${testidPrefix}-attach-chip-${i}`}
          className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-paper-sidebar border border-edge-light text-[11px] text-ink"
        >
          {a.mime?.startsWith("image/") ? <FileImage size={12} /> : <FilePdf size={12} />}
          <span className="max-w-[110px] truncate">{a.name}</span>
          <button
            type="button"
            data-testid={`${testidPrefix}-attach-remove-${i}`}
            onClick={() => setAttachments(attachments.filter((_, idx) => idx !== i))}
            className="text-ink-3 hover:text-brand"
            aria-label="remove"
          >
            <X size={11} />
          </button>
        </div>
      ))}
    </div>
  );
}

export function AttachmentGallery({ attachments, testidPrefix = "att" }) {
  const [lightboxIndex, setLightboxIndex] = useState(null);

  if (!attachments || attachments.length === 0) return null;

  const imageIndices = attachments
    .map((a, i) => (a.mime?.startsWith("image/") ? i : -1))
    .filter((i) => i >= 0);

  return (
    <>
      <div className="mt-4 flex gap-3 flex-wrap" data-testid={`${testidPrefix}-gallery`}>
        {attachments.map((a, i) => {
          const url = `data:${a.mime};base64,${a.data}`;
          const isImage = (a.mime || "").startsWith("image/");
          const commonInner = (
            <>
              {isImage ? (
                <img src={url} alt={a.name} className="w-10 h-10 object-cover rounded-md" />
              ) : (
                <div className="w-10 h-10 rounded-md bg-brand/10 grid place-items-center">
                  <FilePdf size={18} className="text-brand" />
                </div>
              )}
              <div className="min-w-0">
                <div className="text-xs font-medium text-ink truncate max-w-[160px]">{a.name}</div>
                <div className="text-[10px] font-mono text-ink-3">
                  {(a.size || 0) < 1024 ? `${a.size || 0} B` : `${Math.round((a.size || 0) / 1024)} KB`}
                </div>
              </div>
            </>
          );
          if (isImage) {
            return (
              <button
                key={i}
                type="button"
                onClick={() => setLightboxIndex(imageIndices.indexOf(i))}
                data-testid={`${testidPrefix}-item-${i}`}
                className="group inline-flex items-center gap-2 px-2 py-1.5 rounded-lg border border-edge-light bg-paper-sidebar hover:border-brand transition-colors text-left"
              >
                {commonInner}
              </button>
            );
          }
          return (
            <a
              key={i}
              href={url}
              download={a.name}
              target="_blank"
              rel="noreferrer"
              data-testid={`${testidPrefix}-item-${i}`}
              className="group inline-flex items-center gap-2 px-2 py-1.5 rounded-lg border border-edge-light bg-paper-sidebar hover:border-brand transition-colors"
            >
              {commonInner}
            </a>
          );
        })}
      </div>
      {lightboxIndex !== null && (
        <ImageLightbox
          images={imageIndices.map((i) => attachments[i])}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndex={setLightboxIndex}
          testid={`${testidPrefix}-lightbox`}
        />
      )}
    </>
  );
}

export function ImageLightbox({ images, index, onClose, onIndex, testid = "image-lightbox" }) {
  const current = images[index];
  const url = current ? `data:${current.mime};base64,${current.data}` : "";

  const go = useCallback(
    (delta) => {
      const next = (index + delta + images.length) % images.length;
      onIndex(next);
    },
    [index, images.length, onIndex]
  );

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
    };
    document.addEventListener("keydown", onKey);
    // lock body scroll
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [go, onClose]);

  if (!current) return null;

  return (
    <div
      data-testid={testid}
      onClick={onClose}
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-ink/85 backdrop-blur-sm animate-fade-up"
    >
      <div
        className="relative max-w-[92vw] max-h-[88vh] flex flex-col items-center gap-3"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={url}
          alt={current.name}
          className="max-w-full max-h-[75vh] object-contain rounded-2xl shadow-clay-lg bg-paper"
        />
        <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-paper-card border border-edge-light shadow-clay">
          <span className="text-xs font-mono text-ink-2 truncate max-w-[200px]">{current.name}</span>
          <span className="text-[10px] font-mono text-ink-3">{index + 1} / {images.length}</span>
          <a
            href={url}
            download={current.name}
            data-testid={`${testid}-download`}
            className="text-xs font-semibold text-brand hover:text-brand-hover flex items-center gap-1"
          >
            <DownloadSimple size={12} weight="bold" />
            Download
          </a>
        </div>
      </div>

      {images.length > 1 && (
        <>
          <button
            data-testid={`${testid}-prev`}
            onClick={(e) => { e.stopPropagation(); go(-1); }}
            className="absolute left-6 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-paper-card text-ink hover:bg-brand hover:text-paper grid place-items-center shadow-clay transition-colors"
            aria-label="previous"
          >
            <CaretLeft size={18} weight="bold" />
          </button>
          <button
            data-testid={`${testid}-next`}
            onClick={(e) => { e.stopPropagation(); go(1); }}
            className="absolute right-6 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-paper-card text-ink hover:bg-brand hover:text-paper grid place-items-center shadow-clay transition-colors"
            aria-label="next"
          >
            <CaretRight size={18} weight="bold" />
          </button>
        </>
      )}

      <button
        data-testid={`${testid}-close`}
        onClick={onClose}
        className="absolute top-6 right-6 w-11 h-11 rounded-full bg-paper-card text-ink hover:bg-brand hover:text-paper grid place-items-center shadow-clay transition-colors"
        aria-label="close"
      >
        <X size={18} weight="bold" />
      </button>
    </div>
  );
}
