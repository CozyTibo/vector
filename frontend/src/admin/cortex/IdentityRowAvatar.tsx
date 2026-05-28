import { useState } from "react";

export function IdentityRowAvatar({
  url,
  displayName,
}: {
  url: string;
  displayName: string;
}) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return null;
  }
  return (
    <img
      src={url}
      alt=""
      title={displayName}
      className="h-10 w-10 shrink-0 rounded-full border border-stone-200 bg-stone-100 object-cover"
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
    />
  );
}
