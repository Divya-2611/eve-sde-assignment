export default function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onBack,
  pending,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onBack: () => void;
  pending: boolean;
}) {
  return (
    <div
      className="modal-backdrop"
      onClick={onBack}
      role="presentation"
    >
      <div
        className="card modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{title}</h2>
        <p className="muted">{message}</p>
        <div className="card-actions">
          <button
            type="button"
            className="btn-danger"
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? "Please wait…" : confirmLabel}
          </button>
          <button type="button" className="btn-ghost" onClick={onBack}>
            Back
          </button>
        </div>
      </div>
    </div>
  );
}
