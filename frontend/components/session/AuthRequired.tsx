'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { LogIn, ShieldCheck } from 'lucide-react';
import { useT } from '@/lib/i18n';

interface AuthRequiredProps {
  title?: string;
  description?: string;
}

export function AuthRequired({
  title,
  description,
}: AuthRequiredProps) {
  const t = useT();

  return (
    <div className="flex h-full items-center justify-center px-6 py-12">
      <div className="axis-panel max-w-md p-8 text-center">
        <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-lg border border-border bg-muted/45 text-primary">
          <ShieldCheck className="size-5" />
        </div>
        <h2 className="text-2xl font-semibold tracking-[-0.02em]">{title || t('loginRequired')}</h2>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">{description || t('defaultAuthRequired')}</p>
        <Link href="/auth">
          <Button className="mt-6">
            <LogIn className="mr-2 h-4 w-4" />
            {t('loginOrRegister')}
          </Button>
        </Link>
      </div>
    </div>
  );
}
