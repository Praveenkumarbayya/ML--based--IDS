import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Pin the workspace root so Turbopack stops warning about multiple lockfiles.
  turbopack: {
    root: path.join(__dirname),
  },
  // Enables the `node server.js` self-contained bundle used by the Docker image.
  output: "standalone",
};

export default nextConfig;
