/** @type {import('next').NextConfig} */
import path from "path";
const nextConfig = {
  turbopack: {
    root: path.resolve(),
  },
  allowedDevOrigins: ['192.168.0.109','192.168.0.108','172.20.10.4','192.168.2.198','192.168.0.119'],
  devIndicators: false,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
