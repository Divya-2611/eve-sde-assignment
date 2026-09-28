export default function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="alert-error" role="alert">
      {message}
    </p>
  );
}
