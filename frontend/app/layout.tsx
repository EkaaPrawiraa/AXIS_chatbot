import type { Metadata, Viewport } from 'next'
import { Providers } from '@/providers'
import './globals.css'

// Prevent iOS auto-zoom on input focus and keep the layout stable when
// the virtual keyboard opens (keyboard only covers the visual viewport).
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  interactiveWidget: 'resizes-visual',
}

export const metadata: Metadata = {
  title: 'AXIS - Companionship Chatbot',
  description: 'A companionship chatbot architecture with long-term memory for student reflection and support.',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="id" className="bg-background" data-scroll-behavior="smooth" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
