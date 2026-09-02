/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'picsum.photos' },
      { protocol: 'https', hostname: 'upload.wikimedia.org' },
    ],
  },
  async rewrites() {
    // Always proxy API calls in dev so the frontend works out of the box.
    // Override with NEXT_PUBLIC_API_URL (e.g. for a remote backend in prod).
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    if (apiUrl) {
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`,
        },
        {
          source: '/uploads/:path*',
          destination: `${apiUrl}/uploads/:path*`,
        },
        {
          source: '/health',
          destination: `${apiUrl}/health`,
        },
      ];
    }
    return [];
  },
};
module.exports = nextConfig;
