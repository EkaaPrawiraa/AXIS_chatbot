'use client';

import Script from 'next/script';
import { useEffect, useRef, useState } from 'react';

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdApi {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string;
        callback: (response: GoogleCredentialResponse) => void;
      }) => void;
      renderButton: (
        parent: HTMLElement,
        options: { type: string; theme: string; size: string; width: number; text: string; shape: string }
      ) => void;
    };
  };
}

declare global {
  interface Window {
    google?: GoogleIdApi;
  }
}

interface GoogleSignInButtonProps {
  onCredential: (idToken: string) => void;
  disabled?: boolean;
}

export function GoogleSignInButton({ onCredential, disabled }: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scriptReady, setScriptReady] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!scriptReady || !clientId || !containerRef.current || !window.google) return;
    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => onCredential(response.credential),
    });
    containerRef.current.innerHTML = '';
    window.google.accounts.id.renderButton(containerRef.current, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      width: 350,
      text: 'continue_with',
      shape: 'pill',
    });
  }, [scriptReady, clientId]);

  if (!clientId) return null;

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onReady={() => setScriptReady(true)}
      />
      <div
        ref={containerRef}
        aria-disabled={disabled}
        className={disabled ? 'pointer-events-none opacity-50' : undefined}
      />
    </>
  );
}
